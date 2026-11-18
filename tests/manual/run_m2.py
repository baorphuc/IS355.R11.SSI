"""Reproducible M2 runner; logs subprocess stdout/stderr without rewriting it.

Standard setup: Python 3.12 venv + requirements-crypto-ipfs-m2.lock.txt.
Kubo uses a dedicated local repository, loopback API, offline mode, no swarm.
The Kubo repository contains its node identity and MUST NOT be published.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "7227239cff716fc74b5c5ccbe07875be8bb1fc27"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kubo-exe", type=Path, required=True)
    parser.add_argument("--kubo-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/m2/run-01")
    parser.add_argument("--port", type=int, default=15001)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Use CPython 3.12 with the pinned M2 dependencies")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if (out / "commands.json").exists():
        raise RuntimeError("Use a fresh output directory; preserve earlier raw logs")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["IPFS_PATH"] = str(args.kubo_repo.resolve())
    env["PYTHONIOENCODING"] = "utf-8"
    commands = []
    summary = {"baseline": BASELINE, "started_utc": datetime.now(timezone.utc).isoformat(),
               "tests": {}, "real_kubo": "NOT_RUN", "DL-05": "PROPOSED"}
    environment = {"python": sys.version, "executable": sys.executable,
                   "platform": platform.platform(), "baseline": BASELINE,
                   "packages": dict(sorted((d.metadata['Name'], d.version)
                                           for d in importlib.metadata.distributions()))}
    (out / "environment.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")

    def save_state():
        (out / "commands.json").write_text(json.dumps(commands, indent=2), encoding="utf-8")
        (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    def run(label, command):
        entry = {"label": label, "argv": [str(a) for a in command],
                 "cwd": str(ROOT), "started_utc": datetime.now(timezone.utc).isoformat(),
                 "raw_log": label + ".log"}
        commands.append(entry)
        save_state()
        with (out / (label + ".log")).open("wb") as log:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=180)
        entry["exit_code"] = result.returncode
        entry["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save_state()
        print(f"{label}: exit={result.returncode}", flush=True)
        if result.returncode:
            raise RuntimeError(f"{label} failed; see its unmodified raw log")

    python = sys.executable
    kubo = str(args.kubo_exe.resolve())
    hidden = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    daemon = None
    daemon_out = daemon_err = None
    api = f"http://127.0.0.1:{args.port}"
    try:
        run("baseline-unit", [python, "-m", "pytest", "tests/unit/test_crypto.py",
             "tests/unit/test_ipfs.py", "tests/unit/test_e2e_three_files.py", "-vv", "-p", "no:cacheprovider"])
        summary["tests"]["baseline"] = "PASS"
        run("fixture-generation", [python, "-u", "tests/manual/crypto_ipfs_m2.py", "--generate-fixtures"])
        run("all-unit", [python, "-m", "pytest", "tests/unit", "-vv", "-p", "no:cacheprovider"])
        summary["tests"]["all_unit"] = "PASS"
        run("kubo-version", [kubo, "version", "--all"])
        if args.kubo_repo.exists():
            raise RuntimeError("Use a fresh dedicated --kubo-repo; do not touch existing node state")
        run("kubo-init", [kubo, "init", "--profile=test", "--algorithm=ed25519"])
        run("kubo-api-config", [kubo, "config", "Addresses.API", f"/ip4/127.0.0.1/tcp/{args.port}"])
        run("kubo-swarm-config", [kubo, "config", "--json", "Addresses.Swarm", "[]"])
        run("kubo-gateway-config", [kubo, "config", "--json", "Addresses.Gateway", '""'])
        daemon_out = (out / "kubo-daemon.stdout.log").open("wb")
        daemon_err = (out / "kubo-daemon.stderr.log").open("wb")
        commands.append({"label": "kubo-daemon", "argv": [kubo, "daemon", "--offline"],
                         "IPFS_PATH": str(args.kubo_repo.resolve()),
                         "raw_log": ["kubo-daemon.stdout.log", "kubo-daemon.stderr.log"]})
        save_state()
        daemon = subprocess.Popen([kubo, "daemon", "--offline"], cwd=ROOT, env=env,
                                  stdout=daemon_out, stderr=daemon_err, creationflags=hidden)
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            if daemon.poll() is not None:
                raise RuntimeError("Kubo daemon exited; see raw daemon logs")
            try:
                response = requests.post(api + "/api/v0/version", timeout=1)
                response.raise_for_status()
                break
            except requests.RequestException:
                time.sleep(0.25)
        else:
            raise RuntimeError("Kubo API not reachable; see raw daemon logs")
        run("real-kubo", [python, "-u", "tests/manual/crypto_ipfs_m2.py", "--api", api,
                          "--output", str(out / "real-kubo")])
        summary["real_kubo"] = "PASS"
        return 0
    except Exception as error:
        summary["error"] = {"type": type(error).__name__, "message": str(error)}
        print(json.dumps(summary["error"]), flush=True)
        return 1
    finally:
        if daemon is not None and daemon.poll() is None:
            try:
                requests.post(api + "/api/v0/shutdown", timeout=3)
                daemon.wait(timeout=10)
            except (requests.RequestException, subprocess.TimeoutExpired):
                daemon.terminate()
                daemon.wait(timeout=10)
        if daemon is not None:
            summary["daemon_exit_code"] = daemon.returncode
        if daemon_out:
            daemon_out.close()
        if daemon_err:
            daemon_err.close()
        summary["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save_state()
        checksums = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json"}
        (out / "SHA256SUMS.json").write_text(json.dumps(checksums, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

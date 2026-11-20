import { expect } from "chai";
import { ethers } from "hardhat";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { address, context, deploy, loadDeployment, manifestPath, setupIssuer, verify } from "../scripts/deployment";

async function fails(action: Promise<unknown>, message: string) {
  let failure: unknown;
  try { await action; } catch (error) { failure = error; }
  expect(failure).to.be.instanceOf(Error);
  expect((failure as Error).message).to.include(message);
}

describe("deployment validation", function () {
  let dir: string;
  beforeEach(async () => { dir = await mkdtemp(path.join(tmpdir(), "ssi-deployment-")); });
  afterEach(async () => { await rm(dir, { recursive: true, force: true }); });

  it("DV01 rejects wrong chain before transactions", async () => {
    const [admin] = await ethers.getSigners();
    const nonce = await admin.getNonce();
    await fails(context(1), "Unexpected chain ID");
    expect(await admin.getNonce()).to.equal(nonce);
  });

  it("DV02 rejects missing and zero signer", () => {
    for (const invalid of [undefined, ethers.ZeroAddress]) {
      expect(() => address(invalid, "signer")).to.throw("Invalid signer");
    }
  });

  it("DV03 refuses an existing manifest before deployment", async () => {
    const file = manifestPath(dir);
    await writeFile(file, "original");
    const [admin] = await ethers.getSigners();
    const nonce = await admin.getNonce();
    await fails(deploy(dir), "Manifest exists");
    expect(await admin.getNonce()).to.equal(nonce);
    expect(await readFile(file, "utf8")).to.equal("original");
  });

  it("DV04 creates a separately identified and verifiable deployment", async () => {
    await writeFile(manifestPath(dir), "original");
    const m = await deploy(dir, "second");
    expect((await loadDeployment(dir, "second")).m).to.deep.equal(m);
    expect(await readFile(manifestPath(dir), "utf8")).to.equal("original");
    await fails(deploy(dir, "second"), "Manifest exists");
  });

  it("DV05 detects lost Registry binding", async () => {
    const m = await deploy(dir);
    const sbt = await ethers.getContractAt("IdentitySBT", m.IdentitySBT);
    await sbt.revokeRole(await sbt.REGISTRY_ROLE(), m.SSIRegistry);
    await fails(verify(m), "Missing REGISTRY_ROLE");
  });

  it("DV06 detects wrong Gate references", async () => {
    const m = await deploy(dir);
    const gate = await ethers.deployContract("GatedService", [m.SSIRegistry, m.IdentitySBT]);
    await fails(verify({ ...m, GatedService: await gate.getAddress() }), "Wrong Gate dependencies");
  });

  it("DV07 repeated setup preserves binding and sends no transaction", async () => {
    const [admin, issuer] = await ethers.getSigners();
    const m = await deploy(dir);
    const nonce = await admin.getNonce();
    await setupIssuer(dir, undefined, m.SSIRegistry, issuer.address);
    expect(await admin.getNonce()).to.equal(nonce + 1);
    await setupIssuer(dir, undefined, m.SSIRegistry, issuer.address);
    expect(await admin.getNonce()).to.equal(nonce + 1);
  });

  it("DV08 grants only the configured Issuer on the verified Registry", async () => {
    const [, issuer] = await ethers.getSigners();
    const m = await deploy(dir);
    await fails(setupIssuer(dir, undefined, m.IdentitySBT, issuer.address), "Registry differs");
    await setupIssuer(dir, undefined, m.SSIRegistry, issuer.address);
    const registry = await ethers.getContractAt("SSIRegistry", m.SSIRegistry);
    expect(await registry.hasRole(await registry.ISSUER_ROLE(), issuer.address)).to.equal(true);
  });

  it("DV09 rejects missing dependency bytecode", async () => {
    const m = await deploy(dir);
    await fails(verify({ ...m, IdentitySBT: m.deployer }), "Missing bytecode: IdentitySBT");
  });
});

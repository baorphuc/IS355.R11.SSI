import { ethers, network } from "hardhat";
import { link, mkdir, readFile, readdir, rmdir, unlink, writeFile } from "node:fs/promises";
import path from "node:path";
import { randomUUID } from "node:crypto";
import type { ContractTransactionResponse, TransactionRequest } from "ethers";

export class ValidationError extends Error {}
export function check(ok: unknown, message: string): asserts ok {
  if (!ok) throw new ValidationError(message);
}

export function address(value: string | undefined, label: string) {
  check(value && ethers.isAddress(value) && value !== ethers.ZeroAddress, "Invalid " + label);
  return ethers.getAddress(value);
}

export async function context(expected = network.config.chainId) {
  const chainId = BigInt(await ethers.provider.send("eth_chainId", []));
  check(expected !== undefined && chainId === BigInt(expected), "Unexpected chain ID");
  const [signer] = await ethers.getSigners();
  const admin = address(signer?.address, "signer");
  const genesis = await ethers.provider.getBlock(0);
  check(genesis?.hash, "Missing genesis block");
  return { network: network.name, chainId: chainId.toString(), genesisHash: genesis.hash, deployer: admin };
}

const names = ["IdentitySBT", "SSIRegistry", "GatedService"] as const;
type Name = typeof names[number];
type Addresses = Record<Name, string>;
type Receipt = { hash: string; blockHash: string; blockNumber: number };
type Manifest = Awaited<ReturnType<typeof context>> & Addresses & {
  timestamp: string; transactions: Record<Name | "binding", Receipt>;
};

export const DEPLOYMENT_GAS_CEILINGS = {
  IdentitySBT: 8_899_558n,
  SSIRegistry: 14_431_531n,
  binding: 1_000_000n,
  GatedService: 1_696_813n,
  grantRole: 1_000_000n,
} as const;
export type DeploymentStep = keyof typeof DEPLOYMENT_GAS_CEILINGS;

export type DeploymentFeeConfig = {
  maxFeePerGas: bigint;
  maxPriorityFeePerGas: bigint;
};
export type DeploymentOverrides = DeploymentFeeConfig & { gasLimit: bigint };
export type RecordedTransaction = {
  hash: string;
  wait(): Promise<{ status: number | null; blockNumber: number; blockHash: string | null } | null>;
};

const SEPOLIA_CHAIN_ID = "11155111";
const maxFeeEnv = "SSI_DEPLOY_MAX_FEE_GWEI";
const priorityFeeEnv = "SSI_DEPLOY_MAX_PRIORITY_FEE_GWEI";

function parseGwei(value: string | undefined, name: string) {
  const normalized = value?.trim();
  check(normalized && /^(?:0|[1-9]\d*)(?:\.\d{1,9})?$/.test(normalized), "Invalid " + name);
  const wei = ethers.parseUnits(normalized, "gwei");
  check(wei > 0n, "Invalid " + name);
  return wei;
}

export function deploymentFeeConfig(
  chainId: string,
  env: Record<string, string | undefined> = process.env,
): DeploymentFeeConfig | undefined {
  if (chainId !== SEPOLIA_CHAIN_ID) return undefined;
  check(Boolean(env[maxFeeEnv]?.trim()) && Boolean(env[priorityFeeEnv]?.trim()),
    "Sepolia requires " + maxFeeEnv + " and " + priorityFeeEnv);
  const maxFeePerGas = parseGwei(env[maxFeeEnv], maxFeeEnv);
  const maxPriorityFeePerGas = parseGwei(env[priorityFeeEnv], priorityFeeEnv);
  check(maxPriorityFeePerGas <= maxFeePerGas, "Deployment priority fee exceeds max fee");
  return { maxFeePerGas, maxPriorityFeePerGas };
}

export function deploymentOverrides(
  step: DeploymentStep,
  estimate: bigint,
  fees: DeploymentFeeConfig,
): DeploymentOverrides {
  const gasLimit = DEPLOYMENT_GAS_CEILINGS[step];
  check(estimate <= gasLimit, "Gas estimate exceeds ceiling for " + step);
  return { ...fees, gasLimit };
}

async function guardedOverrides(
  step: DeploymentStep,
  transaction: TransactionRequest,
  sender: string,
  fees: DeploymentFeeConfig | undefined,
): Promise<DeploymentOverrides | undefined> {
  if (!fees) return undefined;
  const estimate = await ethers.provider.estimateGas({ ...transaction, from: sender });
  return deploymentOverrides(step, estimate, fees);
}

export async function recordTransaction(key: string, tx: RecordedTransaction): Promise<Receipt> {
  console.log(key, tx.hash);
  const receipt = await tx.wait();
  check(receipt?.status === 1 && receipt.blockHash, "Transaction failed: " + key);
  return { hash: tx.hash, blockNumber: receipt.blockNumber, blockHash: receipt.blockHash };
}

export function manifestPath(dir: string, id?: string) {
  if (id !== undefined) check(/^[a-zA-Z0-9_]{1,64}$/.test(id), "Invalid deployment ID");
  return path.join(dir, network.name + (id ? "." + id : "") + ".json");
}

export async function verify(m: Addresses & { deployer: string }) {
  for (const name of names) {
    check(await ethers.provider.getCode(address(m[name], name)) !== "0x", "Missing bytecode: " + name);
  }
  const sbt = await ethers.getContractAt("IdentitySBT", m.IdentitySBT);
  const registry = await ethers.getContractAt("SSIRegistry", m.SSIRegistry);
  const gate = await ethers.getContractAt("GatedService", m.GatedService);
  check(await registry.identitySBT() === m.IdentitySBT, "Wrong Registry binding");
  check(await sbt.hasRole(await sbt.REGISTRY_ROLE(), m.SSIRegistry), "Missing REGISTRY_ROLE");
  check(await gate.sbt() === m.IdentitySBT && await gate.registry() === m.SSIRegistry, "Wrong Gate dependencies");
  check(await sbt.hasRole(await sbt.DEFAULT_ADMIN_ROLE(), m.deployer), "Missing SBT admin");
  check(await registry.hasRole(await registry.DEFAULT_ADMIN_ROLE(), m.deployer), "Missing Registry admin");
  return registry;
}

export async function loadDeployment(dir: string, id?: string) {
  const current = await context();
  const file = manifestPath(dir, id);
  const m: Manifest = JSON.parse(await readFile(file, "utf8"));
  check(m.network === current.network && m.chainId === current.chainId &&
    m.genesisHash === current.genesisHash && m.transactions, "Unverified legacy manifest or different chain");
  for (const key of [...names, "binding"] as const) {
    const saved = m.transactions[key];
    check(saved?.hash, "Missing transaction: " + key);
    const receipt = await ethers.provider.getTransactionReceipt(saved.hash);
    check(receipt && receipt.status === 1 && receipt.blockHash === saved.blockHash &&
      receipt.blockNumber === saved.blockNumber && receipt.from === m.deployer &&
      (key === "binding" ? receipt.to === m.IdentitySBT : receipt.contractAddress === m[key]),
      "Deployment receipt mismatch: " + key);
  }
  const registry = await verify(m);
  return { file, m, registry, signer: current.deployer };
}

export async function deploy(dir: string, id?: string, issuer?: string) {
  const current = await context();
  if (issuer) address(issuer, "Issuer");
  const fees = deploymentFeeConfig(current.chainId);
  const file = manifestPath(dir, id);
  await mkdir(dir, { recursive: true });
  const lock = path.join(dir, network.name + ".deploy.lock");
  await mkdir(lock).catch(() => { throw new ValidationError("Cannot reserve deployment lock: " + lock); });
  let step = "manifest preflight";
  const addresses = {} as Addresses;
  const transactions = {} as Manifest["transactions"];
  async function record(key: keyof typeof transactions, tx: ContractTransactionResponse) {
    transactions[key] = await recordTransaction(key, tx);
  }
  async function create(name: Name, args: string[]) {
    step = "deploy " + name;
    const factory = await ethers.getContractFactory(name);
    const request = await factory.getDeployTransaction(...args);
    const overrides = await guardedOverrides(name, request, current.deployer, fees);
    const contract = overrides ? await factory.deploy(...args, overrides) : await factory.deploy(...args);
    await record(name, contract.deploymentTransaction()!);
    addresses[name] = await contract.getAddress();
    return contract;
  }
  try {
    const files = await readdir(dir);
    check(!files.some(f => f.toLowerCase() === path.basename(file).toLowerCase()) && (id !== undefined || !files.some(f =>
      f.endsWith(".json") && (f.startsWith(network.name + ".") || f.startsWith(network.name + "-")))),
      "Manifest exists; choose a new SSI_DEPLOYMENT_ID");
    const sbt = await create("IdentitySBT", [current.deployer]);
    await create("SSIRegistry", [current.deployer, addresses.IdentitySBT]);
    step = "bind Registry";
    const binding = await guardedOverrides(
      "binding",
      await sbt.setRegistry.populateTransaction(addresses.SSIRegistry),
      current.deployer,
      fees,
    );
    await record("binding", binding
      ? await sbt.setRegistry(addresses.SSIRegistry, binding)
      : await sbt.setRegistry(addresses.SSIRegistry));
    await create("GatedService", [addresses.IdentitySBT, addresses.SSIRegistry]);
    step = "verify contracts and roles";
    const m: Manifest = { ...current, ...addresses, timestamp: new Date().toISOString(), transactions };
    const registry = await verify(m);
    const issuerStatus = issuer ? (await registry.hasRole(await registry.ISSUER_ROLE(), issuer) ? "PASS" : "FAIL") : "NOT CONFIGURED";
    step = "publish manifest";
    const tmp = file + "." + randomUUID() + ".tmp";
    await writeFile(tmp, JSON.stringify(m, null, 2), { flag: "wx" });
    try { await link(tmp, file); } finally { await unlink(tmp); }
    console.log({ ...current, ...addresses, binding: "PASS", DEFAULT_ADMIN_ROLE: "PASS",
      REGISTRY_ROLE: "PASS", ISSUER_ROLE: issuerStatus, manifest: file });
    return m;
  } catch (error) {
    console.error("Stopped at", step, addresses);
    throw error;
  } finally { await rmdir(lock); }
}

export async function setupIssuer(dir: string, id: string | undefined, target: string | undefined, issuer: string | undefined) {
  const account = address(issuer, "Issuer");
  const destination = address(target, "Registry");
  const { m, registry, signer } = await loadDeployment(dir, id);
  const fees = deploymentFeeConfig(m.chainId);
  check(destination === m.SSIRegistry, "Registry differs from manifest");
  check(await registry.hasRole(await registry.DEFAULT_ADMIN_ROLE(), signer), "Signer lacks Registry admin");
  const role = await registry.ISSUER_ROLE();
  if (await registry.hasRole(role, account)) return "ISSUER_ROLE already verified";
  const overrides = await guardedOverrides(
    "grantRole",
    await registry.grantRole.populateTransaction(role, account),
    signer,
    fees,
  );
  const tx = overrides ? await registry.grantRole(role, account, overrides) : await registry.grantRole(role, account);
  await recordTransaction("grantRole", tx);
  check(await registry.hasRole(role, account), "ISSUER_ROLE verification failed");
  return "ISSUER_ROLE PASS";
}

// Provider errors may contain authenticated RPC URLs. Only expose safe diagnostics.
export function report(error: unknown) {
  console.error(error instanceof ValidationError ? error.message :
    "Deployment operation failed (" + (ethers.isError(error, "CALL_EXCEPTION") ? "contract reverted" :
      String((error as NodeJS.ErrnoException)?.code ?? "provider/filesystem error")) + ")");
  process.exitCode = 1;
}

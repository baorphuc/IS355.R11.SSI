import { ethers, network } from "hardhat";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

async function main() {
  const [deployer] = await ethers.getSigners();
  const sbt = await ethers.deployContract("IdentitySBT", [deployer.address]);
  await sbt.waitForDeployment();

  const registry = await ethers.deployContract("SSIRegistry", [deployer.address, await sbt.getAddress()]);
  await registry.waitForDeployment();
  await (await sbt.setRegistry(await registry.getAddress())).wait();

  const gate = await ethers.deployContract("GatedService", [await sbt.getAddress(), await registry.getAddress()]);
  await gate.waitForDeployment();

  const output = {
    network: network.name,
    chainId: (await ethers.provider.getNetwork()).chainId.toString(),
    deployer: deployer.address,
    SSIRegistry: await registry.getAddress(),
    IdentitySBT: await sbt.getAddress(),
    GatedService: await gate.getAddress(),
  };
  await mkdir("deployments", { recursive: true });
  await writeFile(path.join("deployments", `${network.name}.json`), JSON.stringify(output, null, 2));
  console.log(output);
}

main().catch((error) => { console.error(error); process.exitCode = 1; });

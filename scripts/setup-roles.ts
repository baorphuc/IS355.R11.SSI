import { ethers } from "hardhat";

async function main() {
  const registryAddress = process.env.SSI_REGISTRY_ADDRESS;
  const issuerAddress = process.env.ISSUER_ADDRESS;
  if (!registryAddress || !issuerAddress) throw new Error("Thiếu SSI_REGISTRY_ADDRESS hoặc ISSUER_ADDRESS trong .env");

  const registry = await ethers.getContractAt("SSIRegistry", registryAddress);
  const role = await registry.ISSUER_ROLE();
  const tx = await registry.grantRole(role, issuerAddress);
  await tx.wait();
  console.log(`Đã cấp ISSUER_ROLE cho ${issuerAddress}; tx=${tx.hash}`);
}

main().catch((error) => { console.error(error); process.exitCode = 1; });

import "@nomicfoundation/hardhat-ethers";
import "@nomicfoundation/hardhat-chai-matchers";
import "dotenv/config";
import { HardhatUserConfig } from "hardhat/config";

const sepoliaUrl = process.env.SEPOLIA_RPC_URL ?? "";
const deployerKey = process.env.DEPLOYER_PRIVATE_KEY ?? "";

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.24",
    settings: { optimizer: { enabled: true, runs: 200 }, evmVersion: "cancun" },
  },
  networks: {
    hardhat: { chainId: 31337 },
    localhost: { url: process.env.LOCAL_RPC_URL ?? "http://127.0.0.1:8545" },
    ...(sepoliaUrl && deployerKey
      ? { sepolia: { url: sepoliaUrl, accounts: [deployerKey], chainId: 11155111 } }
      : {}),
  },
};

export default config;

import { address, check, loadDeployment, report } from "./deployment";

// The main deployment creates the Gate. This entry point verifies it in place.
async function main() {
  const { m, file } = await loadDeployment("deployments", process.env.SSI_DEPLOYMENT_ID);
  check(address(process.env.IDENTITY_SBT_ADDRESS, "SBT") === m.IdentitySBT &&
    address(process.env.SSI_REGISTRY_ADDRESS, "Registry") === m.SSIRegistry, "Dependencies differ from manifest");
  console.log({ network: m.network, chainId: m.chainId, GatedService: m.GatedService, manifest: file });
}

main().catch(report);

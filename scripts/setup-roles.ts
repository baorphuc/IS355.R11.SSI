import { report, setupIssuer } from "./deployment";

setupIssuer("deployments", process.env.SSI_DEPLOYMENT_ID, process.env.SSI_REGISTRY_ADDRESS, process.env.ISSUER_ADDRESS)
  .then(console.log).catch(report);

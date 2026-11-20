import { deploy, report } from "./deployment";

deploy("deployments", process.env.SSI_DEPLOYMENT_ID, process.env.ISSUER_ADDRESS || undefined).catch(report);

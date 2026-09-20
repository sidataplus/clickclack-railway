import {
  defineRailway,
  github,
  preserve,
  project,
  service,
  volume,
} from "railway/iac";

// Author-only configuration. Use this in a NEW, dedicated Railway project.
// scripts/author.py supplies stable bootstrap values from a gitignored file.
// No randomness is generated during config evaluation or on subsequent plans.
export default defineRailway(() => {
  const repo = process.env.CC_TEMPLATE_REPO;
  if (!repo || !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo)) {
    throw new Error("Set CC_TEMPLATE_REPO to the published owner/repository, or use scripts/author.py.");
  }
  const sizeMB = Number(process.env.CC_VOLUME_SIZE_MB || "1024");
  if (!Number.isInteger(sizeMB) || sizeMB < 512) {
    throw new Error("CC_VOLUME_SIZE_MB must be an integer of at least 512.");
  }
  const data = volume("clickclack-data", {
    region: process.env.CC_VOLUME_REGION || "us-west2",
    sizeMB,
  });
  const clickclack = service("ClickClack", {
    source: github(repo, { branch: process.env.CC_TEMPLATE_BRANCH || "main" }),
    replicas: 1,
    healthcheck: "/readyz",
    healthcheckTimeout: 120,
    volumeMounts: { "/app/data": data },
    env: {
      PORT: "8080",
      CLICKCLACK_DATA: "/app/data",
      CLICKCLACK_PASSWORD_AUTH_ENABLED: "true",
      CLICKCLACK_DEV_BOOTSTRAP: "false",
      CLICKCLACK_METRICS_ENABLED: "false",
      CC_BOOTSTRAP_MODE: "sqlite",
      CC_BOOTSTRAP_EMAIL: process.env.CC_BOOTSTRAP_EMAIL || preserve(),
      CC_BOOTSTRAP_NAME: process.env.CC_BOOTSTRAP_NAME || "Admin",
      CC_BOOTSTRAP_PASSWORD: process.env.CC_BOOTSTRAP_PASSWORD || preserve(),
    },
  });
  return project("clickclack", { resources: [clickclack, data] });
});

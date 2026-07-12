import { servePublicDocs } from "./docs-lib.mjs";

const portIndex = process.argv.findIndex((arg) => arg === "--port" || arg === "-p");
const requestedPort =
  portIndex >= 0 && process.argv[portIndex + 1] ? Number(process.argv[portIndex + 1]) : undefined;
const hostIndex = process.argv.findIndex((arg) => arg === "--host");
const requestedHost = hostIndex >= 0 && process.argv[hostIndex + 1] ? process.argv[hostIndex + 1] : undefined;

const serverInfo = await servePublicDocs({
  host: requestedHost || process.env.HOST || "127.0.0.1",
  port: requestedPort || Number(process.env.PORT) || 4173,
});

console.log(`OBI documentation server running at ${serverInfo.url}`);

process.on("SIGINT", () => {
  serverInfo.server.close(() => process.exit(0));
});

process.on("SIGTERM", () => {
  serverInfo.server.close(() => process.exit(0));
});

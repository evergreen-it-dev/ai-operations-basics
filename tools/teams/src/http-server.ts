import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import type { Transport } from "@modelcontextprotocol/sdk/shared/transport.js";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";

type ServerFactory = () => McpServer;

async function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (chunk: Buffer) => chunks.push(chunk));
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

async function handleMcp(
  req: IncomingMessage,
  res: ServerResponse,
  createMcpServer: ServerFactory,
) {
  const server = createMcpServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const transport = new StreamableHTTPServerTransport({}) as unknown as Transport;
  res.on("close", () => {
    transport.close?.().catch?.(() => {});
  });
  await server.connect(transport);

  const rawTransport = transport as unknown as StreamableHTTPServerTransport;
  if (req.method === "POST") {
    const raw = await readBody(req);
    let body: unknown;
    try {
      body = JSON.parse(raw);
    } catch {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "invalid JSON" }));
      return;
    }
    await rawTransport.handleRequest(req, res, body);
  } else {
    await rawTransport.handleRequest(req, res);
  }
}

export function startHttpServer(port: number, createMcpServer: ServerFactory): void {
  const httpServer = createServer((req, res) => {
    const url = req.url ?? "";
    if (url === "/mcp" || url.startsWith("/mcp?")) {
      handleMcp(req, res, createMcpServer).catch((err) => {
        console.error("MCP handler error:", err);
        if (!res.headersSent) {
          res.writeHead(500).end();
        }
      });
    } else if (url === "/health" || url === "/") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ status: "ok", service: "teams-mcp" }));
    } else {
      res.writeHead(404).end();
    }
  });

  httpServer.listen(port, () => {
    console.error(`Teams MCP HTTP server listening on port ${port}`);
  });
}

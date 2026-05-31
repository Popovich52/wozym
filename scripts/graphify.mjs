import fs from "node:fs/promises";
import path from "node:path";
import madge from "madge";

const root = process.cwd();
const docsDir = path.join(root, "docs");
const graphMdPath = path.join(docsDir, "project-graph.md");
const graphMmdPath = path.join(docsDir, "project-graph.mmd");
const graphJsonPath = path.join(docsDir, "project-graph.index.json");

function normalizePosix(filePath) {
  return filePath.replace(/\\/g, "/");
}

function toFrontendNode(raw) {
  const n = normalizePosix(raw).replace(/^\.\//, "");
  if (n.startsWith("frontend/src/")) return `fe:${n.slice("frontend/src/".length)}`;
  if (n.startsWith("shared/")) return `shared:${n.slice("shared/".length)}`;
  if (n.startsWith("src/")) return `fe:${n.slice("src/".length)}`;
  return `fe:${n}`;
}

async function walk(dir) {
  const out = [];
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.name === "__pycache__") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...(await walk(full)));
    } else if (entry.isFile()) {
      out.push(full);
    }
  }
  return out;
}

function pythonModuleFromFile(filePath) {
  const rel = normalizePosix(path.relative(path.join(root, "backend"), filePath));
  if (!rel.startsWith("app/")) return null;
  const noExt = rel.replace(/\.py$/, "");
  const parts = noExt.split("/");
  if (parts[parts.length - 1] === "__init__") parts.pop();
  return parts.join(".");
}

function parseImportModule(raw) {
  return raw.trim().split(/\s+as\s+/)[0].trim();
}

function resolveRelativeImport(currentModule, moduleExpr) {
  const match = /^(\.+)(.*)$/.exec(moduleExpr);
  if (!match) return moduleExpr;

  const dots = match[1].length;
  const rest = match[2].replace(/^\./, "");

  const basePackage = currentModule.split(".").slice(0, -1);
  const up = Math.max(0, dots - 1);
  const targetBase = basePackage.slice(0, Math.max(0, basePackage.length - up));
  const restParts = rest ? rest.split(".").filter(Boolean) : [];
  return [...targetBase, ...restParts].join(".");
}

function toBackendNode(moduleName) {
  if (moduleName === "app") return "be:app";
  if (!moduleName.startsWith("app.")) return null;
  return `be:${moduleName.slice("app.".length)}`;
}

function sanitizeMermaidId(node) {
  return node.replace(/[^a-zA-Z0-9_]/g, "_");
}

function sanitizeLabel(node) {
  return node.replace(/"/g, "'");
}

async function buildFrontendGraph() {
  const projectRoots = [path.join(root, "frontend", "src"), path.join(root, "shared")];
  const result = await madge(projectRoots, {
    baseDir: root,
    includeNpm: false,
    fileExtensions: ["ts", "tsx", "js", "jsx"],
    tsConfig: path.join(root, "frontend", "tsconfig.json"),
  });

  const obj = result.obj();
  const edges = [];
  const nodes = new Set();

  for (const [fromRaw, depsRaw] of Object.entries(obj)) {
    const from = toFrontendNode(fromRaw);
    nodes.add(from);

    for (const depRaw of depsRaw) {
      const depNorm = normalizePosix(depRaw).replace(/^\.\//, "");
      if (!depNorm.startsWith("frontend/src/") && !depNorm.startsWith("shared/") && !depNorm.startsWith("src/")) {
        continue;
      }

      const to = toFrontendNode(depNorm);
      nodes.add(to);
      edges.push([from, to]);
    }
  }

  return { nodes: [...nodes], edges };
}

async function buildBackendGraph() {
  const files = (await walk(path.join(root, "backend", "app"))).filter((f) => f.endsWith(".py"));
  const edges = [];
  const nodes = new Set();

  for (const file of files) {
    const moduleName = pythonModuleFromFile(file);
    if (!moduleName) continue;

    const fromNode = toBackendNode(moduleName);
    if (!fromNode) continue;
    nodes.add(fromNode);

    const content = await fs.readFile(file, "utf8");
    const lines = content.split(/\r?\n/);

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line || line.startsWith("#")) continue;

      const fromMatch = /^from\s+([\.\w]+)\s+import\s+/.exec(line);
      if (fromMatch) {
        const resolvedModule = resolveRelativeImport(moduleName, fromMatch[1]);
        const toNode = toBackendNode(resolvedModule);
        if (toNode) {
          nodes.add(toNode);
          edges.push([fromNode, toNode]);
        }
        continue;
      }

      const importMatch = /^import\s+(.+)$/.exec(line);
      if (importMatch) {
        const imports = importMatch[1].split(",").map((chunk) => parseImportModule(chunk));
        for (const imp of imports) {
          const toNode = toBackendNode(imp);
          if (toNode) {
            nodes.add(toNode);
            edges.push([fromNode, toNode]);
          }
        }
      }
    }
  }

  return { nodes: [...nodes], edges };
}

function dedupeEdges(edges) {
  const seen = new Set();
  const out = [];
  for (const [a, b] of edges) {
    const key = `${a}=>${b}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push([a, b]);
  }
  return out;
}

function buildMermaid(frontendGraph, backendGraph) {
  const allNodes = [...frontendGraph.nodes, ...backendGraph.nodes];
  const allEdges = dedupeEdges([...frontendGraph.edges, ...backendGraph.edges]);

  const lines = ["flowchart LR", "  subgraph FE[Frontend + Shared]"];

  for (const node of frontendGraph.nodes.sort()) {
    lines.push(`    ${sanitizeMermaidId(node)}[\"${sanitizeLabel(node)}\"]`);
  }
  lines.push("  end");
  lines.push("  subgraph BE[Backend]");
  for (const node of backendGraph.nodes.sort()) {
    lines.push(`    ${sanitizeMermaidId(node)}[\"${sanitizeLabel(node)}\"]`);
  }
  lines.push("  end");

  for (const [from, to] of allEdges) {
    lines.push(`  ${sanitizeMermaidId(from)} --> ${sanitizeMermaidId(to)}`);
  }

  return {
    mermaid: lines.join("\n"),
    nodeCount: allNodes.length,
    edgeCount: allEdges.length,
    edges: allEdges,
    nodes: allNodes,
  };
}

async function main() {
  await fs.mkdir(docsDir, { recursive: true });

  const frontendGraph = await buildFrontendGraph();
  const backendGraph = await buildBackendGraph();
  const graph = buildMermaid(frontendGraph, backendGraph);

  const now = new Date().toISOString();

  const markdown = [
    "# Project Graph (Graphify)",
    "",
    `Generated: ${now}`,
    "",
    `Nodes: ${graph.nodeCount}`,
    `Edges: ${graph.edgeCount}`,
    "",
    "```mermaid",
    graph.mermaid,
    "```",
    "",
    "## Source",
    "",
    "- Frontend/Shared: TypeScript import graph via madge",
    "- Backend: Python import graph via static parser",
  ].join("\n");

  const json = {
    generatedAt: now,
    counts: {
      nodes: graph.nodeCount,
      edges: graph.edgeCount,
      frontendNodes: frontendGraph.nodes.length,
      backendNodes: backendGraph.nodes.length,
    },
    nodes: graph.nodes.sort(),
    edges: graph.edges.map(([from, to]) => ({ from, to })),
  };

  await fs.writeFile(graphMmdPath, `${graph.mermaid}\n`, "utf8");
  await fs.writeFile(graphMdPath, `${markdown}\n`, "utf8");
  await fs.writeFile(graphJsonPath, `${JSON.stringify(json, null, 2)}\n`, "utf8");

  process.stdout.write(`[graphify] updated docs/project-graph.md, docs/project-graph.mmd, docs/project-graph.index.json (${graph.nodeCount} nodes, ${graph.edgeCount} edges)\n`);
}

main().catch((error) => {
  process.stderr.write(`[graphify] failed: ${error?.stack || error}\n`);
  process.exit(1);
});

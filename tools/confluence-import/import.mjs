#!/usr/bin/env node
/**
 * Масовий імпорт Confluence у Markdown через REST (не MCP).
 *
 * Дерево сторінок — як у Folio confluence import: child/page з пагінацією,
 * тіло body.export_view, сторінка з дітьми стає текою і index.md, лист — файл.md.
 *
 *   node import.mjs --url 'https://host/wiki/spaces/KEY/overview'
 *   node import.mjs --url 'https://host/wiki/spaces/KEY/pages/123/Title'
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { htmlToMarkdown } from "./lib/convert.mjs";
import { parseConfluenceUrl, translitSlug } from "./lib/slug.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024;

function arg(name) {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : undefined;
}

function hasFlag(name) {
  return process.argv.includes(name);
}

function loadKeyFile(text) {
  const out = {};
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq < 0) continue;
    out[line.slice(0, eq).trim()] = line.slice(eq + 1).trim();
  }
  return out;
}

async function readAuth() {
  const file = path.join(ROOT, "workspace/keys/confluence");
  let fromFile = {};
  try {
    fromFile = loadKeyFile(await readFile(file, "utf8"));
  } catch {
    fromFile = {};
  }
  const token = process.env.CONFLUENCE_TOKEN || fromFile.CONFLUENCE_TOKEN || "";
  const email = process.env.CONFLUENCE_EMAIL || fromFile.CONFLUENCE_EMAIL || "";
  if (!token) {
    throw new Error(
      "Немає токена. Поклади CONFLUENCE_TOKEN у workspace/keys/confluence (шаблон workspace.example/keys/confluence.example).",
    );
  }
  const header = email
    ? `Basic ${Buffer.from(`${email}:${token}`).toString("base64")}`
    : `Bearer ${token}`;
  return { header };
}

async function confluenceGet(base, restPath, auth) {
  const url = restPath.startsWith("http") ? restPath : `${base}${restPath.startsWith("/") ? "" : "/"}${restPath}`;
  let lastErr;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await fetch(url, {
        headers: { Authorization: auth.header, Accept: "application/json" },
        signal: AbortSignal.timeout(30_000),
      });
      if (!res.ok) throw new Error(`Confluence API ${res.status} ${res.statusText} для ${restPath}`);
      return await res.json();
    } catch (err) {
      lastErr = err;
      if (attempt < 2) await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
    }
  }
  throw lastErr;
}

async function confluenceGetBinary(base, restPath, auth) {
  const url = restPath.startsWith("http") ? restPath : `${base}${restPath.startsWith("/") ? "" : "/"}${restPath}`;
  const res = await fetch(url, { headers: { Authorization: auth.header }, signal: AbortSignal.timeout(60_000) });
  if (!res.ok) throw new Error(`download ${res.status}`);
  const buf = Buffer.from(await res.arrayBuffer());
  if (buf.length > MAX_ATTACHMENT_BYTES) throw new Error("too large");
  return buf;
}

async function fetchChildren(base, pageId, auth) {
  const out = [];
  let start = 0;
  for (;;) {
    const data = await confluenceGet(base, `/rest/api/content/${pageId}/child/page?limit=100&start=${start}`, auth);
    out.push(...(data.results ?? []));
    if ((data.size ?? data.results?.length ?? 0) < 100) break;
    start += 100;
  }
  return out;
}

async function walkTree(base, rootId, auth, includeChildren) {
  const tree = new Map();
  async function walk(id) {
    const kids = includeChildren ? await fetchChildren(base, id, auth) : [];
    const ids = kids.map((kid) => String(kid.id));
    tree.set(String(id), ids);
    for (const kid of ids) await walk(kid);
  }
  await walk(rootId);
  return tree;
}

async function fetchPage(base, id, auth, children) {
  const data = await confluenceGet(
    base,
    `/rest/api/content/${id}?expand=body.export_view,space,ancestors`,
    auth,
  );
  const webui = data._links?.webui || "";
  const tiny = data._links?.base || base;
  return {
    id: String(data.id),
    title: data.title || `page-${id}`,
    spaceKey: data.space?.key || "",
    spaceName: data.space?.name || data.space?.key || "confluence",
    children,
    html: data.body?.export_view?.value || "",
    sourceUrl: webui.startsWith("http") ? webui : `${tiny.replace(/\/$/, "")}${webui}`,
  };
}

async function fetchAttachments(base, id, auth) {
  try {
    const data = await confluenceGet(base, `/rest/api/content/${id}/child/attachment?limit=100`, auth);
    return (data.results ?? [])
      .filter((item) => item._links?.download)
      .map((item) => ({
        title: item.title,
        download: item._links.download,
        bytes: item.extensions?.fileSize ?? null,
      }));
  } catch {
    return [];
  }
}

function assignPaths(rootId, pages) {
  const rel = new Map();
  rel.set(rootId, "index.md");
  function assign(id, dir) {
    const page = pages.get(id);
    if (!page) return;
    const used = new Set();
    for (const kid of page.children.filter((child) => pages.has(child))) {
      let slug = translitSlug(pages.get(kid).title);
      let n = 2;
      while (used.has(slug)) slug = `${translitSlug(pages.get(kid).title)}-${n++}`;
      used.add(slug);
      const hasKids = pages.get(kid).children.some((child) => pages.has(child));
      rel.set(kid, hasKids ? `${dir}${slug}/index.md` : `${dir}${slug}.md`);
      if (hasKids) assign(kid, `${dir}${slug}/`);
    }
  }
  assign(rootId, "");
  return rel;
}

function yamlQuote(value) {
  return `"${String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
}

function relLink(fromRel, toRel) {
  let rel = path.posix.relative(path.posix.dirname(`/${fromRel}`), `/${toRel}`);
  if (!rel.startsWith(".")) rel = `./${rel}`;
  return rel;
}

async function resolveRoot(parsed, auth) {
  if (parsed.pageId) return { id: parsed.pageId, homepageId: null };
  if (parsed.isSpace && parsed.spaceKey) {
    const space = await confluenceGet(parsed.base, `/rest/api/space/${encodeURIComponent(parsed.spaceKey)}?expand=homepage`, auth);
    const id = space.homepage?.id;
    if (!id) throw new Error(`У спейсі ${parsed.spaceKey} немає домашньої сторінки.`);
    return { id: String(id), homepageId: String(id) };
  }
  if (parsed.spaceKey && parsed.titleGuess) {
    const cql = `space="${parsed.spaceKey}" and title="${parsed.titleGuess.replace(/"/g, "")}"`;
    const found = await confluenceGet(parsed.base, `/rest/api/content/search?cql=${encodeURIComponent(cql)}&limit=1`, auth);
    const id = found.results?.[0]?.id;
    if (!id) throw new Error(`Сторінку «${parsed.titleGuess}» у спейсі ${parsed.spaceKey} не знайдено.`);
    return { id: String(id), homepageId: null };
  }
  throw new Error("У URL немає ні спейсу, ні id сторінки.");
}

async function main() {
  const pageUrl = arg("--url");
  if (!pageUrl) {
    console.error("Потрібен --url: адреса спейсу або кореневої сторінки.");
    process.exit(2);
  }
  const includeChildren = !hasFlag("--only-page");
  const outRoot = path.resolve(ROOT, arg("--out") || "context/docs/confluence");
  const auth = await readAuth();
  const parsed = parseConfluenceUrl(pageUrl);
  const { id: rootId, homepageId } = await resolveRoot(parsed, auth);
  process.stderr.write(`Корінь ${rootId}, діти: ${includeChildren ? "так" : "ні"}\n`);
  const tree = await walkTree(parsed.base, rootId, auth, includeChildren);
  const pages = new Map();
  for (const [id, children] of tree) {
    const page = await fetchPage(parsed.base, id, auth, children);
    pages.set(id, page);
    process.stderr.write(`  ${page.title}\n`);
  }
  const root = pages.get(String(rootId));
  const spaceSlug = translitSlug(root.spaceName || root.spaceKey || "confluence");
  const nest = homepageId && String(rootId) === homepageId ? "" : `${translitSlug(root.title)}/`;
  const relPaths = assignPaths(String(rootId), pages);
  const destDir = path.join(outRoot, spaceSlug);
  const links = new Map();
  for (const [id, rel] of relPaths) links.set(id, null);
  const imagesByPage = new Map();

  for (const [id, page] of pages) {
    const rel = `${nest}${relPaths.get(id)}`;
    const filesDir = path.join(path.dirname(path.join(destDir, rel)), "_files");
    const images = new Map();
    const attachments = await fetchAttachments(parsed.base, id, auth);
    for (const att of attachments) {
      if (att.bytes !== null && att.bytes > MAX_ATTACHMENT_BYTES) continue;
      try {
        const buf = await confluenceGetBinary(parsed.base, att.download, auth);
        const safe = att.title.replace(/[^A-Za-z0-9._-]/g, "_") || "file";
        await mkdir(filesDir, { recursive: true });
        await writeFile(path.join(filesDir, safe), buf);
        const fromPage = path.posix.join(path.posix.dirname(rel) === "." ? "" : path.posix.dirname(rel), "_files", safe);
        const link = path.posix.relative(path.posix.dirname(rel), fromPage) || safe;
        const href = link.startsWith(".") ? link : `./${link}`;
        images.set(att.title, href);
        images.set(safe, href);
        images.set(encodeURIComponent(att.title), href);
      } catch {
        // один файл не валить сторінку
      }
    }
    imagesByPage.set(id, images);
  }

  for (const [id, rel] of relPaths) {
    const full = `${nest}${rel}`;
    links.set(id, full);
  }

  let written = 0;
  for (const [id, page] of pages) {
    const rel = `${nest}${relPaths.get(id)}`;
    const linkMap = new Map();
    for (const [otherId, otherRel] of links) {
      if (otherId === id) continue;
      linkMap.set(otherId, relLink(rel, otherRel));
    }
    const md = htmlToMarkdown(page.html, { base: parsed.base, links: linkMap, images: imagesByPage.get(id) });
    const body = [
      "---",
      `title: ${yamlQuote(page.title)}`,
      `confluenceId: ${yamlQuote(page.id)}`,
      `sourceUrl: ${yamlQuote(page.sourceUrl)}`,
      "---",
      "",
      `# ${page.title}`,
      "",
      md || "_Сторінка без видимого тексту._",
      "",
    ].join("\n");
    const abs = path.join(destDir, rel);
    await mkdir(path.dirname(abs), { recursive: true });
    await writeFile(abs, body, "utf8");
    written += 1;
  }
  process.stderr.write(`Готово: ${written} сторінок → ${path.relative(ROOT, destDir)}\n`);
}

const isDirect = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isDirect) {
  main().catch((err) => {
    console.error(err instanceof Error ? err.message : String(err));
    process.exit(1);
  });
}

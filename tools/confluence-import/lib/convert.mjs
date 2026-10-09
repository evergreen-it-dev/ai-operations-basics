import TurndownService from "turndown";
import { gfm } from "turndown-plugin-gfm";

const PANEL_KIND = [
  [/note|information/i, "NOTE"],
  [/tip|success/i, "TIP"],
  [/warning|caution/i, "WARNING"],
  [/error|problem/i, "CAUTION"],
];

function classTokens(node) {
  return new Set(String(node.className || "").split(/\s+/).filter(Boolean));
}

function quoteLines(content) {
  return content
    .trim()
    .split("\n")
    .map((line) => `> ${line}`.trimEnd())
    .join("\n");
}

export function stripConfluenceCruft(html) {
  return String(html || "")
    .replace(/<(style|script)\b[^>]*>[\s\S]*?<\/\1>/gi, "")
    .replace(/<!\[CDATA\[[\s\S]*?\]\]>/g, "")
    .replace(/<div[^>]*class=(['"])[^'"]*(?:rbtoc|toc-macro)[^'"]*\1[^>]*>[\s\S]*?<\/div>/gi, "")
    .replace(/<p[^>]*>\s*<a[^>]*name=(['"])[^'"]*\1[^>]*><\/a>\s*<\/p>/gi, "");
}

export function flattenTableCells(html) {
  return html.replace(/<(td|th)\b([^>]*)>([\s\S]*?)<\/\1>/gi, (_m, tag, attrs, inner) => {
    const flat = inner
      .replace(/<br[^>]*>/gi, "¶BR¶")
      .replace(/<\/(p|div|h[1-6])>/gi, "¶BR¶")
      .replace(/<(p|div|h[1-6])[^>]*>/gi, "")
      .replace(/<li[^>]*>/gi, "¶BR¶• ")
      .replace(/<\/?(ul|ol|li)[^>]*>/gi, "")
      .replace(/[\r\n]+/g, " ")
      .replace(/(¶BR¶\s*)+/g, "¶BR¶")
      .replace(/^¶BR¶|¶BR¶$/g, "");
    return `<${tag}${attrs}>${flat}</${tag}>`;
  });
}

function buildTurndown() {
  const td = new TurndownService({ headingStyle: "atx", codeBlockStyle: "fenced", bulletListMarker: "-" });
  td.use(gfm);
  td.remove(["style", "script"]);
  td.addRule("confluence-panels", {
    filter: (node) => {
      if (node.nodeName !== "DIV") return false;
      const tokens = classTokens(node);
      if (tokens.has("code")) return false;
      return tokens.has("confluence-information-macro") || tokens.has("aui-message") || tokens.has("panel");
    },
    replacement: (content, node) => {
      const cls = node.className || "";
      const kind = PANEL_KIND.find(([re]) => re.test(cls))?.[1];
      if (!kind && !/confluence-information-macro|aui-message/.test(cls)) return `\n\n${content.trim()}\n\n`;
      return `\n\n> [!${kind || "NOTE"}]\n${quoteLines(content)}\n\n`;
    },
  });
  td.addRule("confluence-code", {
    filter: (node) => node.nodeName === "PRE" && /syntaxhighlighter|code/.test(node.className || ""),
    replacement: (_c, node) => {
      const params = node.getAttribute("data-syntaxhighlighter-params") || "";
      const lang = (params.match(/brush:\s*([a-z0-9]+)/i) || [])[1] || "";
      return `\n\n\`\`\`${lang}\n${(node.textContent || "").replace(/\n$/, "")}\n\`\`\`\n\n`;
    },
  });
  td.addRule("confluence-tasks", {
    filter: (node) => node.nodeName === "LI" && /task-list|inline-task/.test(`${node.parentNode?.className || ""} ${node.className || ""}`),
    replacement: (content, node) => {
      const checked = /checked/.test(node.className || "") || node.querySelector?.("input[checked]");
      return `- [${checked ? "x" : " "}] ${content.trim()}\n`;
    },
  });
  td.addRule("confluence-iframe", {
    filter: "iframe",
    replacement: (_c, node) => {
      const src = (node.getAttribute("src") || "").trim();
      if (!src) return "";
      const title = (node.getAttribute("title") || src).replace(/[[\]]/g, "").trim();
      return `\n\n[${title}](${src})\n\n`;
    },
  });
  return td;
}

const td = buildTurndown();

function rewriteHref(href, ctx) {
  if (!href) return href;
  if (/\/(?:display\/~|people\/)/.test(href) || /confluence-userlink|user-mention/.test(href)) return null;
  const id = href.match(/\/pages\/(\d+)/)?.[1] || href.match(/[?&]pageId=(\d+)/)?.[1];
  if (id && ctx.links?.has(id)) return ctx.links.get(id);
  if (href.startsWith("http")) return href;
  if (ctx.base && href.startsWith("/")) return `${new URL(ctx.base).origin}${href}`;
  return href;
}

export function htmlToMarkdown(html, ctx = {}) {
  const cleaned = flattenTableCells(stripConfluenceCruft(html));
  td.addRule("links-rewrite", {
    filter: "a",
    replacement: (content, node) => {
      const raw = node.getAttribute("href") || "";
      if (/confluence-userlink|user-mention/.test(node.className || "") || /\/(?:display\/~|people\/)/.test(raw)) {
        return content.trim();
      }
      const href = rewriteHref(raw, ctx) || raw;
      if (!content.trim()) return href ? `<${href}>` : "";
      return `[${content.trim() === raw.trim() ? href : content}](${href})`;
    },
  });
  td.addRule("img-rewrite", {
    filter: (node) => node.nodeName === "IMG" && !/emoticon|emoji/.test(node.className || ""),
    replacement: (_c, node) => {
      const src = node.getAttribute("src") || "";
      const alt = (node.getAttribute("alt") || "").replace(/[[\]]/g, "");
      const local = ctx.images?.get(src) || ctx.images?.get(src.split("/").pop() || "");
      if (local) return `![${alt}](${local})`;
      if (!src) return alt;
      const abs = src.startsWith("http") ? src : ctx.base ? `${ctx.base}${src.startsWith("/") ? "" : "/"}${src}` : src;
      return alt ? `[${alt}](${abs})` : `<${abs}>`;
    },
  });
  let md;
  try {
    md = td.turndown(cleaned);
  } finally {
    td.rules.array = td.rules.array.filter((rule) => rule.name !== "links-rewrite" && rule.name !== "img-rewrite");
  }
  return md.replace(/¶BR¶/g, "<br>").replace(/\n{3,}/g, "\n\n").trim();
}

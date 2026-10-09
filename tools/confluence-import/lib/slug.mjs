const CYRILLIC_TO_LATIN = {
  я: "ya", ю: "yu", ж: "zh", ч: "ch", ш: "sh", щ: "shch", х: "kh", ц: "ts",
  є: "ye", ї: "yi", і: "i", ґ: "g", й: "y", ь: "", ъ: "",
  а: "a", б: "b", в: "v", г: "g", д: "d", е: "e", ё: "yo", з: "z", и: "i",
  к: "k", л: "l", м: "m", н: "n", о: "o", п: "p", р: "r", с: "s", т: "t",
  у: "u", ф: "f", ы: "y", э: "e",
};

export function translitSlug(input) {
  const lower = String(input ?? "").trim().toLowerCase();
  let out = "";
  for (const ch of lower) out += CYRILLIC_TO_LATIN[ch] ?? ch;
  const slug = out.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return slug || "page";
}

export function parseConfluenceUrl(pageUrl) {
  let url;
  try {
    url = new URL(pageUrl);
  } catch {
    throw new Error("Це не URL. Потрібна адреса спейсу або кореневої сторінки Confluence.");
  }
  const path = url.pathname;
  const wikiAt = path.indexOf("/wiki");
  const base = wikiAt >= 0 ? `${url.origin}${path.slice(0, wikiAt)}/wiki` : url.origin.replace(/\/$/, "");
  const rest = wikiAt >= 0 ? path.slice(wikiAt + "/wiki".length) : path;
  const pageId = rest.match(/\/pages\/(\d+)/)?.[1] || url.searchParams.get("pageId") || null;
  const spaceFromPath = rest.match(/\/spaces\/([^/]+)/)?.[1] || rest.match(/\/display\/([^/]+)/)?.[1] || null;
  const displayTitle = rest.match(/\/display\/[^/]+\/(.+)/)?.[1];
  const isSpace = Boolean(spaceFromPath) && !pageId && !displayTitle && !/\/pages\//.test(rest);
  const titleGuess = displayTitle
    ? decodeURIComponent(displayTitle).replace(/\+/g, " ")
    : undefined;
  return { base, pageId, spaceKey: spaceFromPath, isSpace, titleGuess };
}

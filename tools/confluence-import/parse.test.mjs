import assert from "node:assert/strict";
import test from "node:test";
import { htmlToMarkdown } from "./lib/convert.mjs";
import { parseConfluenceUrl, translitSlug } from "./lib/slug.mjs";

test("space overview is a space, not a page", () => {
  const parsed = parseConfluenceUrl("https://wiki.example.com/wiki/spaces/TEAM/overview");
  assert.equal(parsed.base, "https://wiki.example.com/wiki");
  assert.equal(parsed.spaceKey, "TEAM");
  assert.equal(parsed.isSpace, true);
  assert.equal(parsed.pageId, null);
});

test("page url keeps the numeric id", () => {
  const parsed = parseConfluenceUrl("https://wiki.example.com/wiki/spaces/TEAM/pages/42/Hello");
  assert.equal(parsed.pageId, "42");
  assert.equal(parsed.isSpace, false);
  assert.equal(parsed.spaceKey, "TEAM");
});

test("viewpage query is a page", () => {
  const parsed = parseConfluenceUrl("https://wiki.example.com/wiki/pages/viewpage.action?pageId=99");
  assert.equal(parsed.pageId, "99");
  assert.equal(parsed.isSpace, false);
});

test("cyrillic title becomes a latin slug", () => {
  assert.equal(translitSlug("Команда продажу"), "komanda-prodazhu");
});

test("export view html becomes markdown", () => {
  const md = htmlToMarkdown(
    `<div class="confluence-information-macro note"><p>Дивись</p></div><table><tr><th>A</th></tr><tr><td><p>один</p></td></tr></table>`,
  );
  assert.match(md, /\[!NOTE\]/);
  assert.match(md, /\| A \|/);
  assert.match(md, /один/);
});

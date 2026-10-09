import DOMPurify from "dompurify";
import { JSDOM } from "jsdom";
import { marked } from "marked";

// Create a JSDOM window for DOMPurify in Node.js environment
const window = new JSDOM("").window;
const createDOMPurify = DOMPurify(window as any);

// Configure marked for Teams compatibility
marked.setOptions({
  gfm: true, // GitHub Flavored Markdown
  breaks: true, // Convert \n to <br>
});

/**
 * Converts Markdown text to sanitized HTML
 * @param markdown The markdown text to convert
 * @returns Sanitized HTML string
 */
export async function markdownToHtml(markdown: string): Promise<string> {
  // Convert Markdown to HTML
  const rawHtml = await marked(markdown);

  // Sanitize HTML for security - allow common formatting tags safe for Teams
  const cleanHtml = createDOMPurify.sanitize(rawHtml, {
    ALLOWED_TAGS: [
      "p",
      "br",
      "strong",
      "em",
      "b",
      "i",
      "u",
      "s",
      "del",
      "a",
      "ul",
      "ol",
      "li",
      "h1",
      "h2",
      "h3",
      "h4",
      "h5",
      "h6",
      "blockquote",
      "code",
      "pre",
      "hr",
      "table",
      "thead",
      "tbody",
      "tr",
      "th",
      "td",
      "img",
    ],
    ALLOWED_ATTR: ["href", "target", "src", "alt", "title", "width", "height"],
  });

  return cleanHtml;
}

/**
 * Basic HTML sanitization for user-provided HTML content
 * @param html The HTML content to sanitize
 * @returns Sanitized HTML string
 */
export function sanitizeHtml(html: string): string {
  return createDOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      "p",
      "br",
      "strong",
      "em",
      "b",
      "i",
      "u",
      "s",
      "del",
      "a",
      "ul",
      "ol",
      "li",
      "h1",
      "h2",
      "h3",
      "h4",
      "h5",
      "h6",
      "blockquote",
      "code",
      "pre",
      "hr",
      "table",
      "thead",
      "tbody",
      "tr",
      "th",
      "td",
      "img",
    ],
    ALLOWED_ATTR: ["href", "target", "src", "alt", "title", "width", "height"],
  });
}

import { describe, expect, it } from "vitest";
import { markdownToHtml, sanitizeHtml } from "../markdown.js";

describe("markdownToHtml", () => {
  it("should convert basic markdown to HTML", async () => {
    const markdown = "**Bold** and _italic_ text";
    const result = await markdownToHtml(markdown);
    expect(result).toContain("<strong>Bold</strong>");
    expect(result).toContain("<em>italic</em>");
  });

  it("should handle links", async () => {
    const markdown = "[Google](https://google.com)";
    const result = await markdownToHtml(markdown);
    expect(result).toContain('<a href="https://google.com">Google</a>');
  });

  it("should handle lists", async () => {
    const markdown = "- Item 1\n- Item 2";
    const result = await markdownToHtml(markdown);
    expect(result).toContain("<ul>");
    expect(result).toContain("<li>Item 1</li>");
    expect(result).toContain("<li>Item 2</li>");
  });

  it("should handle code blocks", async () => {
    const markdown = "```javascript\nconst x = 1;\n```";
    const result = await markdownToHtml(markdown);
    expect(result).toContain("<pre>");
    expect(result).toContain("<code>");
    expect(result).toContain("const x = 1;");
  });

  it("should handle inline code", async () => {
    const markdown = "Use `console.log()` for debugging";
    const result = await markdownToHtml(markdown);
    expect(result).toContain("<code>console.log()</code>");
  });

  it("should convert line breaks", async () => {
    const markdown = "Line 1\nLine 2";
    const result = await markdownToHtml(markdown);
    expect(result).toContain("<br>");
  });

  it("should handle headings", async () => {
    const markdown = "# Heading 1\n## Heading 2";
    const result = await markdownToHtml(markdown);
    expect(result).toContain("<h1>Heading 1</h1>");
    expect(result).toContain("<h2>Heading 2</h2>");
  });

  it("should sanitize potentially dangerous HTML", async () => {
    const markdown = '<script>alert("xss")</script>\n\n**Bold**';
    const result = await markdownToHtml(markdown);
    expect(result).not.toContain("<script>");
    expect(result).not.toContain("alert");
    expect(result).toContain("<strong>Bold</strong>");
  });

  it("should handle empty string", async () => {
    const result = await markdownToHtml("");
    expect(result).toBe("");
  });

  it("should handle plain text", async () => {
    const plainText = "Just plain text";
    const result = await markdownToHtml(plainText);
    expect(result).toContain("Just plain text");
  });
});

describe("sanitizeHtml", () => {
  it("should allow safe HTML tags", () => {
    const html = "<p><strong>Bold</strong> and <em>italic</em></p>";
    const result = sanitizeHtml(html);
    expect(result).toBe("<p><strong>Bold</strong> and <em>italic</em></p>");
  });

  it("should remove script tags", () => {
    const html = '<p>Safe content</p><script>alert("xss")</script>';
    const result = sanitizeHtml(html);
    expect(result).toContain("<p>Safe content</p>");
    expect(result).not.toContain("<script>");
    expect(result).not.toContain("alert");
  });

  it("should allow links with safe attributes", () => {
    const html = '<a href="https://example.com" target="_blank">Link</a>';
    const result = sanitizeHtml(html);
    expect(result).toBe('<a href="https://example.com" target="_blank">Link</a>');
  });

  it("should remove dangerous attributes", () => {
    const html = '<p onclick="alert(\'xss\')" style="color: red;">Text</p>';
    const result = sanitizeHtml(html);
    expect(result).toBe("<p>Text</p>");
  });

  it("should allow images with safe attributes", () => {
    const html = '<img src="https://example.com/image.jpg" alt="Image" width="100">';
    const result = sanitizeHtml(html);
    expect(result).toBe('<img src="https://example.com/image.jpg" alt="Image" width="100">');
  });

  it("should handle empty string", () => {
    const result = sanitizeHtml("");
    expect(result).toBe("");
  });

  it("should handle plain text", () => {
    const result = sanitizeHtml("Plain text");
    expect(result).toBe("Plain text");
  });
});

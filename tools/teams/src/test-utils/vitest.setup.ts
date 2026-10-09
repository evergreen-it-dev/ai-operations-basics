import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./setup.js";

// Start MSW server before all tests
beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
});

// Reset handlers after each test
afterEach(() => {
  server.resetHandlers();
});

// Clean up after all tests
afterAll(() => {
  server.close();
});

// Global test environment setup
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Mock console methods to reduce noise in tests
const originalError = console.error;
console.error = (...args: any[]) => {
  // Suppress specific known warnings/errors during tests
  if (
    typeof args[0] === "string" &&
    (args[0].includes("MSW") ||
      args[0].includes("Warning") ||
      args[0].includes("Failed to initialize"))
  ) {
    return;
  }
  originalError.apply(console, args);
};

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { GraphService } from "../../services/graph.js";
import {
  getUserByEmail,
  getUserById,
  parseMentions,
  processMentionsInHtml,
  searchUsers,
} from "../users.js";

const mockGraphService = {
  getClient: vi.fn(),
} as unknown as GraphService;

const mockClient = {
  api: vi.fn(),
};

describe("User Utilities", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (mockGraphService.getClient as any).mockResolvedValue(mockClient);
  });

  describe("searchUsers", () => {
    it("should search users by display name", async () => {
      const mockUsers = [
        { id: "1", displayName: "John Doe", userPrincipalName: "john.doe@company.com" },
        { id: "2", displayName: "John Smith", userPrincipalName: "john.smith@company.com" },
      ];

      mockClient.api.mockReturnValue({
        get: vi.fn().mockResolvedValue({ value: mockUsers }),
      });

      const result = await searchUsers(mockGraphService, "John", 10);

      expect(result).toEqual([
        { id: "1", displayName: "John Doe", userPrincipalName: "john.doe@company.com" },
        { id: "2", displayName: "John Smith", userPrincipalName: "john.smith@company.com" },
      ]);

      expect(mockClient.api).toHaveBeenCalledWith(
        "/users?$filter=startswith(displayName,'John') or startswith(userPrincipalName,'John')&$top=10&$select=id,displayName,userPrincipalName"
      );
    });

    it("should return empty array when no users found", async () => {
      mockClient.api.mockReturnValue({
        get: vi.fn().mockResolvedValue({ value: [] }),
      });

      const result = await searchUsers(mockGraphService, "NonExistent", 10);
      expect(result).toEqual([]);
    });

    it("should handle errors gracefully", async () => {
      mockClient.api.mockReturnValue({
        get: vi.fn().mockRejectedValue(new Error("Graph API error")),
      });

      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {
        // Mock implementation - do nothing
      });
      const result = await searchUsers(mockGraphService, "John", 10);

      expect(result).toEqual([]);
      expect(consoleSpy).toHaveBeenCalledWith("Error searching users:", expect.any(Error));

      consoleSpy.mockRestore();
    });
  });

  describe("getUserByEmail", () => {
    it("should get user by email", async () => {
      const mockUser = {
        id: "1",
        displayName: "John Doe",
        userPrincipalName: "john.doe@company.com",
      };

      mockClient.api.mockReturnValue({
        get: vi.fn().mockResolvedValue(mockUser),
      });

      const result = await getUserByEmail(mockGraphService, "john.doe@company.com");

      expect(result).toEqual({
        id: "1",
        displayName: "John Doe",
        userPrincipalName: "john.doe@company.com",
      });

      expect(mockClient.api).toHaveBeenCalledWith("/users/john.doe@company.com");
    });

    it("should return null when user not found", async () => {
      mockClient.api.mockReturnValue({
        get: vi.fn().mockRejectedValue(new Error("User not found")),
      });

      const result = await getUserByEmail(mockGraphService, "nonexistent@company.com");
      expect(result).toBeNull();
    });
  });

  describe("getUserById", () => {
    it("should get user by ID", async () => {
      const mockUser = {
        id: "1",
        displayName: "John Doe",
        userPrincipalName: "john.doe@company.com",
      };

      mockClient.api.mockReturnValue({
        select: vi.fn().mockReturnValue({
          get: vi.fn().mockResolvedValue(mockUser),
        }),
      });

      const result = await getUserById(mockGraphService, "1");

      expect(result).toEqual({
        id: "1",
        displayName: "John Doe",
        userPrincipalName: "john.doe@company.com",
      });

      expect(mockClient.api).toHaveBeenCalledWith("/users/1");
    });

    it("should return null when user not found", async () => {
      mockClient.api.mockReturnValue({
        select: vi.fn().mockReturnValue({
          get: vi.fn().mockRejectedValue(new Error("User not found")),
        }),
      });

      const result = await getUserById(mockGraphService, "nonexistent");
      expect(result).toBeNull();
    });
  });

  describe("parseMentions", () => {
    it("should parse simple @mentions", async () => {
      const mockUsers = [
        { id: "1", displayName: "John Doe", userPrincipalName: "john.doe@company.com" },
      ];

      mockClient.api.mockReturnValue({
        get: vi.fn().mockResolvedValue({ value: mockUsers }),
      });

      const result = await parseMentions("Hello @john.doe how are you?", mockGraphService);

      expect(result).toEqual([
        {
          mention: "john.doe",
          users: [{ id: "1", displayName: "John Doe", userPrincipalName: "john.doe@company.com" }],
        },
      ]);
    });

    it("should parse email @mentions", async () => {
      const mockUser = {
        id: "1",
        displayName: "John Doe",
        userPrincipalName: "john.doe@company.com",
      };

      mockClient.api.mockReturnValue({
        get: vi.fn().mockResolvedValue(mockUser),
      });

      const result = await parseMentions("Hello @john.doe@company.com", mockGraphService);

      expect(result).toEqual([
        {
          mention: "john.doe@company.com",
          users: [{ id: "1", displayName: "John Doe", userPrincipalName: "john.doe@company.com" }],
        },
      ]);
    });

    it("should parse quoted @mentions", async () => {
      const mockUsers = [
        { id: "1", displayName: "John Doe", userPrincipalName: "john.doe@company.com" },
      ];

      mockClient.api.mockReturnValue({
        get: vi.fn().mockResolvedValue({ value: mockUsers }),
      });

      const result = await parseMentions('Hello @"John Doe", how are you?', mockGraphService);

      expect(result).toEqual([
        {
          mention: "John Doe",
          users: [{ id: "1", displayName: "John Doe", userPrincipalName: "john.doe@company.com" }],
        },
      ]);
    });

    it("should handle multiple @mentions", async () => {
      mockClient.api
        .mockReturnValueOnce({
          get: vi.fn().mockResolvedValue({
            value: [
              { id: "1", displayName: "John Doe", userPrincipalName: "john.doe@company.com" },
            ],
          }),
        })
        .mockReturnValueOnce({
          get: vi.fn().mockResolvedValue({
            value: [
              { id: "2", displayName: "Jane Smith", userPrincipalName: "jane.smith@company.com" },
            ],
          }),
        });

      const result = await parseMentions("Hello @john.doe and @jane", mockGraphService);

      expect(result).toHaveLength(2);
      expect(result[0].mention).toBe("john.doe");
      expect(result[1].mention).toBe("jane");
    });

    it("should return empty array when no mentions found", async () => {
      const result = await parseMentions("Hello world, no mentions here!", mockGraphService);
      expect(result).toEqual([]);
    });
  });

  describe("processMentionsInHtml", () => {
    it("should process @mentions in HTML content", () => {
      const html = "<p>Hello @john.doe, how are you?</p>";
      const mentionMappings = [{ mention: "john.doe", userId: "1", displayName: "John Doe" }];

      const result = processMentionsInHtml(html, mentionMappings);

      expect(result.content).toBe('<p>Hello <at id="0">John Doe</at>, how are you?</p>');
      expect(result.mentions).toEqual([
        {
          id: 0,
          mentionText: "John Doe",
          mentioned: { user: { id: "1" } },
        },
      ]);
    });

    it("should process quoted @mentions in HTML content", () => {
      const html = '<p>Hello @"John Doe", how are you?</p>';
      const mentionMappings = [{ mention: "John Doe", userId: "1", displayName: "John Doe" }];

      const result = processMentionsInHtml(html, mentionMappings);

      expect(result.content).toBe('<p>Hello <at id="0">John Doe</at>, how are you?</p>');
      expect(result.mentions).toEqual([
        {
          id: 0,
          mentionText: "John Doe",
          mentioned: { user: { id: "1" } },
        },
      ]);
    });

    it("should handle multiple @mentions", () => {
      const html = "<p>Hello @john.doe and @jane.smith!</p>";
      const mentionMappings = [
        { mention: "john.doe", userId: "1", displayName: "John Doe" },
        { mention: "jane.smith", userId: "2", displayName: "Jane Smith" },
      ];

      const result = processMentionsInHtml(html, mentionMappings);

      expect(result.content).toBe(
        '<p>Hello <at id="0">John Doe</at> and <at id="1">Jane Smith</at>!</p>'
      );
      expect(result.mentions).toHaveLength(2);
    });

    it("should return unchanged content when no mappings provided", () => {
      const html = "<p>Hello @john.doe, how are you?</p>";
      const result = processMentionsInHtml(html, []);

      expect(result.content).toBe(html);
      expect(result.mentions).toEqual([]);
    });
  });
});

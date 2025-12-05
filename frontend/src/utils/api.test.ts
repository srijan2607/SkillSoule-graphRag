/**
 * Unit tests for Query API Client
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { sendQuery, APIError } from "./api";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("sendQuery", () => {
  const mockToken = "test-jwt-token";
  const mockQuery = "What skills do I need for data science?";

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("should successfully send query and return response", async () => {
    const mockResponse = {
      query: mockQuery,
      response: "You need Python, statistics, and machine learning skills.",
      sources: [
        {
          node_type: "Skill",
          node_id: "python-001",
          properties: { name: "python" },
        },
      ],
      processing_time_ms: 245,
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const result = await sendQuery(mockQuery, mockToken);

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/query/ask"),
      expect.objectContaining({
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${mockToken}`,
        },
        body: JSON.stringify({ query: mockQuery }),
      })
    );

    expect(result).toEqual(mockResponse);
  });

  it("should handle 400 Bad Request error", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      text: async () => "Invalid query format",
    });

    await expect(sendQuery(mockQuery, mockToken)).rejects.toThrow(
      "Invalid query. Please try again."
    );
  });

  it("should handle 401 Unauthorized error", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      text: async () => "Unauthorized",
    });

    await expect(sendQuery(mockQuery, mockToken)).rejects.toThrow(
      "Not authenticated. Please log in."
    );
  });

  it("should handle 500 Internal Server Error", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: async () => "Internal server error",
    });

    await expect(sendQuery(mockQuery, mockToken)).rejects.toThrow(
      "Server error. Please try again later."
    );
  });

  it("should handle timeout after 10 seconds", async () => {
    // Mock AbortError for timeout
    const abortError = new Error("Aborted");
    abortError.name = "AbortError";
    mockFetch.mockRejectedValueOnce(abortError);

    await expect(sendQuery(mockQuery, mockToken)).rejects.toThrow(
      "Request timed out. Please try again."
    );
  });

  it("should handle network errors", async () => {
    mockFetch.mockRejectedValueOnce(new TypeError("Network request failed"));

    await expect(sendQuery(mockQuery, mockToken)).rejects.toThrow(
      "Connection error. Please check your internet."
    );
  });

  it("should include Authorization header with token", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        query: mockQuery,
        response: "Test response",
        sources: [],
        processing_time_ms: 100,
      }),
    });

    await sendQuery(mockQuery, mockToken);

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: `Bearer ${mockToken}`,
        }),
      })
    );
  });

  it("should create AbortController with timeout signal", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        query: mockQuery,
        response: "Test response",
        sources: [],
        processing_time_ms: 100,
      }),
    });

    await sendQuery(mockQuery, mockToken);

    // Verify fetch was called with an AbortSignal
    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        signal: expect.any(AbortSignal),
      })
    );
  });

  it("should throw APIError with correct properties", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      text: async () => "Bad request",
    });

    try {
      await sendQuery(mockQuery, mockToken);
      expect.fail("Should have thrown APIError");
    } catch (error) {
      expect(error).toBeInstanceOf(APIError);
      expect(error.statusCode).toBe(400);
      expect(error.message).toContain("Invalid query");
    }
  });
});

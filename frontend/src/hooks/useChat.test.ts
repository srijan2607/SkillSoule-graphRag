/**
 * Unit tests for useChat Hook
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useChat } from "./useChat";
import * as apiModule from "@/utils/api";

// Mock the API module
vi.mock("@/utils/api", () => ({
  sendQuery: vi.fn(),
  APIError: class APIError extends Error {
    constructor(message: string, public statusCode?: number) {
      super(message);
      this.name = "APIError";
    }
  },
}));

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
global.localStorage = localStorageMock as any;

// Mock window.location
delete (window as any).location;
window.location = { href: "" } as any;

describe("useChat", () => {
  const mockToken = "test-jwt-token";
  const mockSendQuery = vi.mocked(apiModule.sendQuery);

  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(mockToken);
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it("should initialize with empty messages and not loading", () => {
    const { result } = renderHook(() => useChat());

    expect(result.current.messages).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("should add user message immediately (optimistic UI)", async () => {
    const mockResponse = {
      query: "test query",
      response: "test response",
      sources: [],
      processing_time_ms: 100,
    };

    mockSendQuery.mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("test query");
    });

    // User message should be added immediately
    expect(result.current.messages).toHaveLength(2); // User + assistant
    expect(result.current.messages[0].role).toBe("user");
    expect(result.current.messages[0].content).toBe("test query");
  });

  it("should set loading state while waiting for API response", async () => {
    let resolvePromise: (value: any) => void;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });

    mockSendQuery.mockReturnValueOnce(promise as any);

    const { result } = renderHook(() => useChat());

    // Start sending message
    act(() => {
      result.current.sendMessage("test query");
    });

    // Should be loading
    await waitFor(() => {
      expect(result.current.isLoading).toBe(true);
    });

    // Resolve the API call
    await act(async () => {
      resolvePromise!({
        query: "test query",
        response: "test response",
        sources: [],
        processing_time_ms: 100,
      });
    });

    // Should no longer be loading
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });

  it("should add assistant message on successful response", async () => {
    const mockResponse = {
      query: "What is Python?",
      response: "Python is a programming language.",
      sources: [
        {
          node_type: "Skill",
          node_id: "python-001",
          properties: { name: "python" },
        },
      ],
      processing_time_ms: 245,
    };

    mockSendQuery.mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("What is Python?");
    });

    // Should have user message + assistant message
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[1].role).toBe("assistant");
    expect(result.current.messages[1].content).toBe(
      "Python is a programming language."
    );
    expect(result.current.messages[1].sources).toEqual(mockResponse.sources);
  });

  it("should handle error and add error message to chat", async () => {
    const mockError = new apiModule.APIError("Server error. Please try again later.", 500);
    mockSendQuery.mockRejectedValueOnce(mockError);

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("test query");
    });

    // Should have user message + error message
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[1].role).toBe("assistant");
    expect(result.current.messages[1].content).toContain("Server error");
    expect(result.current.error).toBe("Server error. Please try again later.");
  });

  it("should handle missing token", async () => {
    localStorageMock.getItem.mockReturnValueOnce(null);

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("test query");
    });

    // Should have error message
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].content).toContain("Not authenticated");
    expect(result.current.error).toBe("Not authenticated. Please log in.");
  });

  it("should handle 401 error by redirecting to login", async () => {
    const mockError = new apiModule.APIError("Not authenticated. Please log in.", 401);
    mockSendQuery.mockRejectedValueOnce(mockError);

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("test query");
    });

    // Should clear token
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("token");
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("user");
  });

  it("should not send empty messages", async () => {
    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("");
    });

    expect(mockSendQuery).not.toHaveBeenCalled();
    expect(result.current.messages).toHaveLength(0);
  });

  it("should trim whitespace from messages", async () => {
    const mockResponse = {
      query: "test query",
      response: "test response",
      sources: [],
      processing_time_ms: 100,
    };

    mockSendQuery.mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("  test query  ");
    });

    expect(result.current.messages[0].content).toBe("test query");
    expect(mockSendQuery).toHaveBeenCalledWith("test query", mockToken);
  });

  it("should clear messages", () => {
    const { result } = renderHook(() => useChat());

    // Add some messages first
    act(() => {
      result.current.sendMessage("test");
    });

    // Clear messages
    act(() => {
      result.current.clearMessages();
    });

    expect(result.current.messages).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  it("should include JWT token in API call", async () => {
    const mockResponse = {
      query: "test",
      response: "response",
      sources: [],
      processing_time_ms: 100,
    };

    mockSendQuery.mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("test");
    });

    expect(mockSendQuery).toHaveBeenCalledWith("test", mockToken);
  });

  it("should handle timeout errors", async () => {
    const mockError = new apiModule.APIError("Request timed out. Please try again.");
    mockSendQuery.mockRejectedValueOnce(mockError);

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("test query");
    });

    expect(result.current.messages[1].content).toContain("Request timed out");
  });
});

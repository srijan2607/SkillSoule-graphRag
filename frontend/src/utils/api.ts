/**
 * Query API Client
 *
 * Handles communication with the backend query endpoint.
 * Implements timeout handling and proper error management.
 */

import { SourceNode } from "@/types/chat";
import { API_BASE_URL, API_ENDPOINTS, API_TIMEOUT_MS, ERROR_MESSAGES, HTTP_STATUS_MESSAGES } from "@/constants/api";

/**
 * Query request payload
 */
export interface QueryRequest {
  query: string;
  session_id?: string;
}

/**
 * Query response from backend
 */
export interface QueryResponse {
  query: string;
  response: string;
  sources: SourceNode[];
  processing_time_ms: number;
  metadata?: {
    intent?: string;
    graph_nodes_count?: number;
    graph_relationships_count?: number;
    traversal_intents?: string[];
    response_generation_skipped?: boolean;
    pipeline_errors_detected?: string[];
    response_generation_error?: string;
    response_generation_failed?: boolean;
    metrics?: QueryMetrics;
    [key: string]: any;
  };
  metrics?: QueryMetrics;
}

/**
 * Detailed metrics from backend
 */
export interface QueryMetrics {
  total_time_ms: number;
  stage_timings?: {
    intent_analysis?: number;
    vector_search?: number;
    graph_traversal?: number;
    context_construction?: number;
    response_generation?: number;
  };
  [key: string]: any;
}

/**
 * Custom error class for API errors
 */
export class APIError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public originalError?: unknown
  ) {
    super(message);
    this.name = "APIError";
  }
}

/**
 * Send query to backend RAG system
 *
 * @param query - User's question/query
 * @param token - JWT authentication token
 * @param sessionId - Optional session ID for tracking query processing
 * @returns Query response with answer and sources
 * @throws APIError on network, timeout, or server errors
 */
export async function sendQuery(
  query: string,
  token: string,
  sessionId?: string
): Promise<QueryResponse> {
  // Create abort controller for timeout handling
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

  try {
    const requestBody: QueryRequest = { query };
    if (sessionId) {
      requestBody.session_id = sessionId;
    }

    const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.QUERY}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify(requestBody),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // Handle HTTP errors
    if (!response.ok) {
      const errorText = await response.text().catch(() => "Unknown error");

      switch (response.status) {
        case 400:
          throw new APIError(ERROR_MESSAGES.INVALID_QUERY, 400);
        case 401:
          throw new APIError(ERROR_MESSAGES.NOT_AUTHENTICATED, 401);
        case 500:
          throw new APIError(ERROR_MESSAGES.SERVER_ERROR, 500);
        default:
          throw new APIError(
            `API error: ${response.status} - ${errorText}`,
            response.status
          );
      }
    }

    const data: QueryResponse = await response.json();
    return data;

  } catch (error) {
    clearTimeout(timeoutId);

    // Handle abort/timeout
    if (error instanceof Error && error.name === "AbortError") {
      throw new APIError(ERROR_MESSAGES.TIMEOUT);
    }

    // Handle network errors
    if (error instanceof TypeError) {
      throw new APIError(ERROR_MESSAGES.CONNECTION_ERROR, undefined, error);
    }

    // Re-throw APIError as-is
    if (error instanceof APIError) {
      throw error;
    }

    // Wrap unknown errors
    throw new APIError(
      ERROR_MESSAGES.UNEXPECTED_ERROR,
      undefined,
      error
    );
  }
}

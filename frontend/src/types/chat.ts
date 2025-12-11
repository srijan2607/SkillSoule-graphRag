import { NetworkInsights } from './query';

/**
 * Message interface for chat messages
 */
export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: SourceNode[];
  metadata?: MessageMetadata;
  processingTime?: number;
  network_insights?: NetworkInsights | null;
}

/**
 * Metadata from backend query response
 */
export interface MessageMetadata {
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
}

/**
 * Query metrics from backend
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
 * Source node from knowledge graph
 */
export interface SourceNode {
  node_type: string;
  node_id: string;
  properties: Record<string, any>;
}

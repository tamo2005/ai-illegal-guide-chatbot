/**
 * API Type Definitions
 * Defines the structure of data exchanged between frontend and backend
 */

export interface ChatQuery {
  text: string;
  location?: string | null;
  session_id?: string | null;
}

export interface RiskAssessment {
  overall_risk: 'low' | 'medium' | 'high';
  recommendation?: string;
  safety_score?: number;
  warnings?: string[];
}

export interface ContextSource {
  id: string;
  title: string;
  content: string;
  relevance_score: number;
  source_type: 'knowledge_base' | 'document' | 'web' | 'database';
  metadata?: Record<string, any>;
}

export interface ChatResponse {
  query: string;
  response: string;
  confidence_score: number;
  risk_assessment: RiskAssessment;
  context_sources?: ContextSource[];
  processing_time?: number;
  session_id?: string;
  timestamp?: number;
}

export interface ApiError {
  code: number;
  message: string;
  type: string;
  details?: any;
  timestamp: number;
  path: string;
  request_id?: string;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: ApiError;
  message?: string;
}

export interface HealthCheckResponse {
  success: boolean;
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: number;
  version: string;
  checks?: {
    api_key: boolean;
    rag_service: boolean;
    knowledge_base: boolean;
  };
}

export interface StreamChatResponse {
  type: 'start' | 'chunk' | 'end' | 'error';
  content?: string;
  metadata?: {
    confidence_score?: number;
    risk_assessment?: RiskAssessment;
    context_sources?: ContextSource[];
  };
  error?: string;
}
/**
 * Chat Type Definitions
 * Defines the structure of data used within the chat interface
 */

export type MessageRole = 'user' | 'assistant' | 'system';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  metadata?: {
    confidence_score?: number;
    risk_assessment?: {
      overall_risk: 'low' | 'medium' | 'high';
      recommendation?: string;
      safety_score?: number;
      warnings?: string[];
    };
    context_sources?: Array<{
      id: string;
      title: string;
      relevance_score: number;
    }>;
    processing_time?: number;
  };
  isLoading?: boolean;
  error?: string;
}

export interface ChatSession {
  id: string;
  messages: Message[];
  created_at: number;
  updated_at: number;
  title?: string;
  location?: string;
}

export interface ChatState {
  currentSession: ChatSession | null;
  sessions: ChatSession[];
  isLoading: boolean;
  error: string | null;
  isConnected: boolean;
}

export interface SendMessageOptions {
  location?: string;
  sessionId?: string;
  streaming?: boolean;
}

export interface ChatMetrics {
  totalMessages: number;
  averageResponseTime: number;
  averageConfidenceScore: number;
  riskDistribution: {
    low: number;
    medium: number;
    high: number;
  };
}
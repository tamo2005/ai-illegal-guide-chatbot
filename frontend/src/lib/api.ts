/**
 * API Client
 * Handles all communication with the FastAPI backend
 */

import { ChatQuery, ChatResponse, ApiResponse, HealthCheckResponse } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public details?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

/**
 * Main API client for the AI chatbot backend
 */
export class ApiClient {
  private baseURL: string;
  private defaultHeaders: Record<string, string>;

  constructor(baseURL = API_BASE_URL) {
    this.baseURL = baseURL;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
  }

  /**
   * Make a raw HTTP request
   */
  private async request<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const config: RequestInit = {
      ...options,
      headers: {
        ...this.defaultHeaders,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);
      
      // Handle non-JSON responses (like SSE streams)
      const contentType = response.headers.get('content-type');
      if (!contentType?.includes('application/json')) {
        if (response.ok) {
          return response as any;
        }
        throw new APIError(
          `HTTP ${response.status}: ${response.statusText}`,
          response.status
        );
      }

      const data = await response.json();

      if (!response.ok) {
        const error = data.error || {};
        throw new APIError(
          error.message || `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          error.code,
          error.details
        );
      }

      return data;
    } catch (error) {
      if (error instanceof APIError) {
        throw error;
      }
      
      // Handle network errors
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new APIError(
          'Network error: Unable to connect to the server',
          0,
          'NETWORK_ERROR'
        );
      }
      
      throw new APIError(
        error instanceof Error ? error.message : 'Unknown error occurred',
        500,
        'UNKNOWN_ERROR'
      );
    }
  }

  /**
   * Health check endpoint
   */
  async healthCheck(): Promise<HealthCheckResponse> {
    return this.request<HealthCheckResponse>('/health');
  }

  /**
   * Send a chat message and get a response
   */
  async sendChatMessage(query: ChatQuery): Promise<ChatResponse> {
    const response = await this.request<ApiResponse<ChatResponse>>('/api/v1/chat', {
      method: 'POST',
      body: JSON.stringify(query),
    });

    if (!response.success || !response.data) {
      throw new APIError(
        response.error?.message || 'Failed to get chat response',
        response.error?.code || 500,
        response.error?.type
      );
    }

    return response.data;
  }

  /**
   * Stream a chat message (Server-Sent Events)
   */
  async streamChatMessage(
    query: ChatQuery,
    onChunk: (chunk: string) => void,
    onMetadata?: (metadata: any) => void,
    onError?: (error: string) => void,
    onComplete?: () => void
  ): Promise<void> {
    try {
      const response = await this.request<Response>('/api/v1/chat/stream', {
        method: 'POST',
        body: JSON.stringify(query),
        headers: {
          ...this.defaultHeaders,
          'Accept': 'text/event-stream',
        },
      });

      if (!response.body) {
        throw new APIError('No response body received', 500);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            onComplete?.();
            break;
          }

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              
              if (data === '[DONE]') {
                onComplete?.();
                return;
              }

              try {
                const parsed = JSON.parse(data);
                
                if (parsed.type === 'error') {
                  onError?.(parsed.error || 'Stream error occurred');
                  return;
                }
                
                if (parsed.type === 'chunk' && parsed.content) {
                  onChunk(parsed.content);
                }
                
                if (parsed.type === 'metadata' && parsed.metadata) {
                  onMetadata?.(parsed.metadata);
                }
              } catch (e) {
                console.warn('Failed to parse SSE data:', data);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    } catch (error) {
      if (error instanceof APIError) {
        onError?.(error.message);
        return;
      }
      onError?.(error instanceof Error ? error.message : 'Stream error occurred');
    }
  }

  /**
   * Get chat history for a session
   */
  async getChatHistory(sessionId: string): Promise<ChatResponse[]> {
    const response = await this.request<ApiResponse<ChatResponse[]>>(
      `/api/v1/chat/history/${sessionId}`
    );

    if (!response.success || !response.data) {
      throw new APIError(
        response.error?.message || 'Failed to get chat history',
        response.error?.code || 500,
        response.error?.type
      );
    }

    return response.data;
  }

  /**
   * Create a new chat session
   */
  async createChatSession(): Promise<{ session_id: string }> {
    const response = await this.request<ApiResponse<{ session_id: string }>>(
      '/api/v1/chat/session',
      { method: 'POST' }
    );

    if (!response.success || !response.data) {
      throw new APIError(
        response.error?.message || 'Failed to create chat session',
        response.error?.code || 500,
        response.error?.type
      );
    }

    return response.data;
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export error class for error handling
export { APIError };
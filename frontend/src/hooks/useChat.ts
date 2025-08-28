/**
 * Custom Chat Hook
 * React hook for managing chat functionality and state
 */

import { useCallback, useEffect, useRef } from 'react';
import { useChatStore } from '../store/chatStore';

import { apiClient } from '@/lib/api';
import { SendMessageOptions } from '@/types/chat';

export const useChat = () => {
    const {
        currentSession,
        sessions,
        isLoading,
        error,
        isConnected,
        createSession,
        loadSession,
        clearCurrentSession,
        sendMessage,
        streamMessage,
        setError,
        setConnected,
        clearError,
        retryLastMessage,
        exportSession,
        importSession,
    } = useChatStore();

    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    // Health check and connection monitoring
    const checkConnection = useCallback(async () => {
        try {
            await apiClient.healthCheck();
            setConnected(true);
            clearError();
        } catch (error) {
            setConnected(false);
            setError('Connection lost. Attempting to reconnect...');
            
            // Auto-reconnect after 5 seconds
            reconnectTimeoutRef.current = setTimeout(() => {
                checkConnection();
            }, 5000);
        }
    }, [setConnected, setError, clearError]);

    // Initialize connection check
    useEffect(() => {
        checkConnection();
        
        // Set up periodic health checks
        const interval = setInterval(checkConnection, 30000); // Check every 30 seconds
        
        return () => {
            clearInterval(interval);
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
        };
    }, [checkConnection]);

    // Enhanced send message with retry logic
    const sendMessageWithRetry = useCallback(
        async (content: string, options: SendMessageOptions = {}) => {
            const maxRetries = 3;
            let attempt = 0;
            
            const attemptSend = async (): Promise<void> => {
                try {
                    if (options.streaming) {
                        await streamMessage(content, options);
                    } else {
                        await sendMessage(content, options);
                    }
                } catch (error) {
                    attempt++;
                    
                    if (attempt < maxRetries && !isConnected) {
                        // Wait and retry if connection is lost
                        await new Promise(resolve => setTimeout(resolve, 2000 * attempt));
                        await checkConnection();
                        
                        if (isConnected) {
                            return attemptSend();
                        }
                    }
                    
                    throw error;
                }
            };
            
            return attemptSend();
        },
        [sendMessage, streamMessage, isConnected, checkConnection]
    );

    // Start a new conversation
    const startNewConversation = useCallback(async () => {
        clearError();
        await createSession();
    }, [createSession, clearError]);

    // Load conversation by ID
    const loadConversation = useCallback(
        async (sessionId: string) => {
            clearError();
            await loadSession(sessionId);
        },
        [loadSession, clearError]
    );

    // Clear current conversation
    const clearConversation = useCallback(() => {
        clearCurrentSession();
        clearError();
    }, [clearCurrentSession, clearError]);

    // Get conversation metrics
    const getMetrics = useCallback(() => {
        if (!currentSession) return null;

        const messages = currentSession.messages.filter(m => m.role === 'assistant' && !m.isLoading && !m.error);
        const totalMessages = messages.length;
        
        if (totalMessages === 0) return null;

        const avgResponseTime = messages.reduce((sum, msg) => {
            return sum + (msg.metadata?.processing_time || 0);
        }, 0) / totalMessages;

        const avgConfidenceScore = messages.reduce((sum, msg) => {
            return sum + (msg.metadata?.confidence_score || 0);
        }, 0) / totalMessages;

        const riskDistribution = messages.reduce(
            (acc, msg) => {
                const risk = msg.metadata?.risk_assessment?.overall_risk || 'medium';
                acc[risk as keyof typeof acc]++;
                return acc;
            },
            { low: 0, medium: 0, high: 0 }
        );

        return {
            totalMessages,
            averageResponseTime: Math.round(avgResponseTime * 100) / 100,
            averageConfidenceScore: Math.round(avgConfidenceScore * 100) / 100,
            riskDistribution,
        };
    }, [currentSession]);

    // Format message for display
    const formatMessage = useCallback((content: string) => {
        // Basic markdown-like formatting
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }, []);

    // Get typing indicator status
    const isTyping = useCallback(() => {
        if (!currentSession) return false;
        const lastMessage = currentSession.messages[currentSession.messages.length - 1];
        return lastMessage?.role === 'assistant' && lastMessage?.isLoading;
    }, [currentSession]);

    // Get last error message
    const getLastError = useCallback(() => {
        if (error) return error;
        
        if (currentSession) {
            const lastMessage = currentSession.messages[currentSession.messages.length - 1];
            if (lastMessage?.error) return lastMessage.error;
        }
        
        return null;
    }, [error, currentSession]);

    // Export current session
    const exportCurrentSession = useCallback(() => {
        if (!currentSession) return null;
        return exportSession();
    }, [currentSession, exportSession]);

    // Import session from JSON
    const importSessionFromJson = useCallback(
        (jsonData: string) => {
            try {
                importSession(jsonData);
                return true;
            } catch (error) {
                setError('Failed to import session: Invalid format');
                return false;
            }
        },
        [importSession, setError]
    );

    return {
        // State
        currentSession,
        sessions,
        isLoading,
        error: getLastError(),
        isConnected,
        
        // Actions
        sendMessage: sendMessageWithRetry,
        startNewConversation,
        loadConversation,
        clearConversation,
        retryLastMessage,
        clearError,
        
        // Utilities
        getMetrics,
        formatMessage,
        isTyping,
        exportCurrentSession,
        importSessionFromJson,
        
        // Connection
        checkConnection,
    };
};

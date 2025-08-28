    /**
     * Chat Store
     * Global state management for chat functionality using Zustand
     */

    import { create } from 'zustand';
    import { devtools, persist } from 'zustand/middleware';
    import { immer } from 'zustand/middleware/immer';
    import { Message, ChatSession, ChatState, SendMessageOptions } from '@/types/chat';
    import { apiClient, APIError } from '@/lib/api';
    import { ChatQuery } from '@/types/api';

    interface ChatActions {
        // Session management
        createSession: () => Promise<void>;
        loadSession: (sessionId: string) => Promise<void>;
        clearCurrentSession: () => void;
        deleteSession: (sessionId: string) => void;
        
        // Message handling
        sendMessage: (content: string, options?: SendMessageOptions) => Promise<void>;
        streamMessage: (content: string, options?: SendMessageOptions) => Promise<void>;
        addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
        updateMessage: (messageId: string, updates: Partial<Message>) => void;
        deleteMessage: (messageId: string) => void;
        
        // UI state
        setLoading: (isLoading: boolean) => void;
        setError: (error: string | null) => void;
        setConnected: (isConnected: boolean) => void;
        
        // Utilities
        clearError: () => void;
        retryLastMessage: () => Promise<void>;
        exportSession: () => string | null;
        importSession: (data: string) => boolean;
        clearAllSessions: () => void;
    }

    type ChatStore = ChatState & ChatActions;

    // Utility functions
    const generateId = (): string => {
        return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
    };

    const generateSessionTitle = (firstMessage: string): string => {
        const trimmed = firstMessage.trim();
        if (!trimmed) return 'New Chat';
        
        const words = trimmed.split(' ').slice(0, 6);
        const title = words.join(' ');
        return title.length < trimmed.length ? `${title}...` : title;
    };

    const validateMessage = (content: string): string | null => {
        if (!content.trim()) return 'Message cannot be empty';
        if (content.length > 10000) return 'Message too long (max 10000 characters)';
        return null;
    };

    // Session operations
    const updateSessionInArray = (
        sessions: ChatSession[], 
        sessionId: string, 
        updates: Partial<ChatSession>
    ): ChatSession[] => {
        const index = sessions.findIndex(s => s.id === sessionId);
        if (index === -1) return sessions;
        
        const updatedSession = { ...sessions[index], ...updates };
        const newSessions = [...sessions];
        newSessions[index] = updatedSession;
        return newSessions;
    };

    export const useChatStore = create<ChatStore>()(
        devtools(
            persist(
                immer((set, get) => ({
                    // Initial state
                    currentSession: null,
                    sessions: [],
                    isLoading: false,
                    error: null,
                    isConnected: true,

                    // Session management
                    createSession: async () => {
                        try {
                            set((state) => {
                                state.isLoading = true;
                                state.error = null;
                            });

                            const newSession: ChatSession = {
                                id: generateId(),
                                messages: [],
                                created_at: Date.now(),
                                updated_at: Date.now(),
                            };

                            set((state) => {
                                state.currentSession = newSession;
                                state.sessions.unshift(newSession);
                                state.isLoading = false;
                            });
                        } catch (error) {
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to create session';
                                state.isLoading = false;
                            });
                            throw error;
                        }
                    },

                    loadSession: async (sessionId: string) => {
                        if (!sessionId) {
                            set((state) => {
                                state.error = 'Invalid session ID';
                            });
                            return;
                        }

                        try {
                            set((state) => {
                                state.isLoading = true;
                                state.error = null;
                            });

                            const session = get().sessions.find(s => s.id === sessionId);
                            if (!session) {
                                throw new Error('Session not found');
                            }

                            set((state) => {
                                state.currentSession = session;
                                state.isLoading = false;
                            });
                        } catch (error) {
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to load session';
                                state.isLoading = false;
                            });
                            throw error;
                        }
                    },

                    clearCurrentSession: () => {
                        set((state) => {
                            state.currentSession = null;
                            state.error = null;
                        });
                    },

                    deleteSession: (sessionId: string) => {
                        set((state) => {
                            state.sessions = state.sessions.filter((s: ChatSession) => s.id !== sessionId);
                            if (state.currentSession?.id === sessionId) {
                                state.currentSession = null;
                            }
                        });
                    },

                    // Message handling
                    sendMessage: async (content: string, options = {}) => {
                        const validation = validateMessage(content);
                        if (validation) {
                            set((state) => {
                                state.error = validation;
                            });
                            return;
                        }

                        let { currentSession } = get();
                        if (!currentSession) {
                            await get().createSession();
                            currentSession = get().currentSession;
                        }

                        if (!currentSession) {
                            set((state) => {
                                state.error = 'Failed to create session';
                            });
                            return;
                        }

                        const userMessage: Message = {
                            id: generateId(),
                            role: 'user',
                            content: content.trim(),
                            timestamp: Date.now(),
                        };

                        const assistantMessageId = generateId();
                        const assistantMessage: Message = {
                            id: assistantMessageId,
                            role: 'assistant',
                            content: '',
                            timestamp: Date.now(),
                            isLoading: true,
                        };

                        // Add both messages
                        get().addMessage(userMessage);
                        get().addMessage(assistantMessage);

                        try {
                            set((state) => {
                                state.isLoading = true;
                                state.error = null;
                            });

                            const query: ChatQuery = {
                                text: content,
                                location: options.location,
                                session_id: currentSession.id,
                            };

                            const response = await apiClient.sendChatMessage(query);

                            get().updateMessage(assistantMessageId, {
                                content: response.response,
                                isLoading: false,
                                metadata: {
                                    confidence_score: response.confidence_score,
                                    risk_assessment: response.risk_assessment,
                                    context_sources: response.context_sources?.map(source => ({
                                        id: source.id,
                                        title: source.title,
                                        relevance_score: source.relevance_score,
                                    })),
                                    processing_time: response.processing_time,
                                },
                            });

                            // Update session title for first user message
                            const session = get().currentSession;
                            if (session && session.messages.filter(m => m.role === 'user').length === 1) {
                                const title = generateSessionTitle(content);
                                set((state) => {
                                    if (state.currentSession) {
                                        state.currentSession.title = title;
                                        state.currentSession.updated_at = Date.now();
                                        state.sessions = updateSessionInArray(
                                            state.sessions, 
                                            session.id, 
                                            { title, updated_at: Date.now() }
                                        );
                                    }
                                });
                            }

                        } catch (error) {
                            const errorMessage = error instanceof APIError 
                                ? error.message 
                                : 'Failed to send message';

                            get().updateMessage(assistantMessageId, {
                                content: 'Sorry, I encountered an error. Please try again.',
                                isLoading: false,
                                error: errorMessage,
                            });

                            set((state) => {
                                state.error = errorMessage;
                            });
                        } finally {
                            set((state) => {
                                state.isLoading = false;
                            });
                        }
                    },

                    streamMessage: async (content: string, options = {}) => {
                        const validation = validateMessage(content);
                        if (validation) {
                            set((state) => {
                                state.error = validation;
                            });
                            return;
                        }

                        let { currentSession } = get();
                        if (!currentSession) {
                            await get().createSession();
                            currentSession = get().currentSession;
                        }

                        if (!currentSession) {
                            set((state) => {
                                state.error = 'Failed to create session';
                            });
                            return;
                        }

                        const userMessage: Message = {
                            id: generateId(),
                            role: 'user',
                            content: content.trim(),
                            timestamp: Date.now(),
                        };

                        const assistantMessageId = generateId();
                        const assistantMessage: Message = {
                            id: assistantMessageId,
                            role: 'assistant',
                            content: '',
                            timestamp: Date.now(),
                            isLoading: true,
                        };

                        get().addMessage(userMessage);
                        get().addMessage(assistantMessage);

                        try {
                            set((state) => {
                                state.isLoading = true;
                                state.error = null;
                            });

                            const query: ChatQuery = {
                                text: content,
                                location: options.location,
                                session_id: currentSession.id,
                            };

                            let accumulatedContent = '';

                            await apiClient.streamChatMessage(
                                query,
                                (chunk: string) => {
                                    accumulatedContent += chunk;
                                    get().updateMessage(assistantMessageId, {
                                        content: accumulatedContent,
                                        isLoading: true,
                                    });
                                },
                                (metadata: any) => {
                                    get().updateMessage(assistantMessageId, { metadata });
                                },
                                (error: string) => {
                                    get().updateMessage(assistantMessageId, {
                                        content: accumulatedContent || 'Sorry, I encountered an error.',
                                        isLoading: false,
                                        error,
                                    });
                                    set((state) => {
                                        state.error = error;
                                        state.isLoading = false;
                                    });
                                },
                                () => {
                                    get().updateMessage(assistantMessageId, {
                                        isLoading: false,
                                    });
                                    set((state) => {
                                        state.isLoading = false;
                                    });
                                }
                            );

                        } catch (error) {
                            const errorMessage = error instanceof APIError 
                                ? error.message 
                                : 'Failed to stream message';

                            get().updateMessage(assistantMessageId, {
                                content: 'Sorry, I encountered an error. Please try again.',
                                isLoading: false,
                                error: errorMessage,
                            });

                            set((state) => {
                                state.error = errorMessage;
                                state.isLoading = false;
                            });
                        }
                    },

                    addMessage: (messageData) => {
                        const message: Message = {
                            id: generateId(),
                            timestamp: Date.now(),
                            ...messageData,
                        };

                        set((state) => {
                            if (state.currentSession) {
                                state.currentSession.messages.push(message);
                                state.currentSession.updated_at = Date.now();
                                
                                state.sessions = updateSessionInArray(
                                    state.sessions,
                                    state.currentSession.id,
                                    { 
                                        messages: [...state.currentSession.messages],
                                        updated_at: Date.now() 
                                    }
                                );
                            }
                        });
                    },

                    updateMessage: (messageId: string, updates: Partial<Message>) => {
                        set((state) => {
                            if (state.currentSession) {
                                const messageIndex = state.currentSession.messages.findIndex((m: Message) => m.id === messageId);
                                if (messageIndex !== -1) {
                                    state.currentSession.messages[messageIndex] = {
                                        ...state.currentSession.messages[messageIndex],
                                        ...updates,
                                    };
                                    
                                    state.sessions = updateSessionInArray(
                                        state.sessions,
                                        state.currentSession.id,
                                        { messages: [...state.currentSession.messages] }
                                    );
                                }
                            }
                        });
                    },

                    deleteMessage: (messageId: string) => {
                        set((state) => {
                            if (state.currentSession) {
                                state.currentSession.messages = state.currentSession.messages.filter(
                                    (m: Message) => m.id !== messageId
                                );
                                
                                state.sessions = updateSessionInArray(
                                    state.sessions,
                                    state.currentSession.id,
                                    { messages: [...state.currentSession.messages] }
                                );
                            }
                        });
                    },

                    // UI state management
                    setLoading: (isLoading: boolean) => {
                        set((state) => {
                            state.isLoading = isLoading;
                        });
                    },

                    setError: (error: string | null) => {
                        set((state) => {
                            state.error = error;
                        });
                    },

                    setConnected: (isConnected: boolean) => {
                        set((state) => {
                            state.isConnected = isConnected;
                        });
                    },

                    clearError: () => {
                        set((state) => {
                            state.error = null;
                        });
                    },

                    retryLastMessage: async () => {
                        const { currentSession } = get();
                        if (!currentSession || currentSession.messages.length < 2) return;

                        const lastUserMessage = [...currentSession.messages]
                            .reverse()
                            .find(m => m.role === 'user');

                        if (!lastUserMessage) return;

                        // Remove failed assistant message
                        const lastMessage = currentSession.messages[currentSession.messages.length - 1];
                        if (lastMessage.role === 'assistant' && (lastMessage.error || lastMessage.isLoading)) {
                            get().deleteMessage(lastMessage.id);
                        }

                        await get().sendMessage(lastUserMessage.content);
                    },

                    exportSession: (): string | null => {
                        const { currentSession } = get();
                        if (!currentSession) return null;

                        try {
                            return JSON.stringify({
                                session: currentSession,
                                exported_at: Date.now(),
                                version: '1.0'
                            }, null, 2);
                        } catch (error) {
                            set((state) => {
                                state.error = 'Failed to export session';
                            });
                            return null;
                        }
                    },

                    importSession: (data: string): boolean => {
                        try {
                            const parsed = JSON.parse(data);
                            if (!parsed.session?.messages || !Array.isArray(parsed.session.messages)) {
                                throw new Error('Invalid format');
                            }

                            const session: ChatSession = {
                                ...parsed.session,
                                id: generateId(),
                                created_at: Date.now(),
                                updated_at: Date.now(),
                            };

                            set((state) => {
                                state.currentSession = session;
                                state.sessions.unshift(session);
                                state.error = null;
                            });

                            return true;
                        } catch (error) {
                            set((state) => {
                                state.error = 'Invalid session data format';
                            });
                            return false;
                        }
                    },

                    clearAllSessions: () => {
                        set((state) => {
                            state.sessions = [];
                            state.currentSession = null;
                            state.error = null;
                        });
                    },
                })),
                {
                    name: 'chat-store',
                    partialize: (state) => ({
                        sessions: state.sessions,
                    }),
                }
            )
        )
    );
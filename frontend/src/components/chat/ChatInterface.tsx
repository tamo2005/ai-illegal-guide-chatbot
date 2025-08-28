'use client'

/**
 * ChatInterface Component
 * Main chat interface with messages, input, and controls
 */

import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, AlertCircle, RefreshCw, Download, Upload } from 'lucide-react';
import { useChat } from '@/hooks/useChat';
import { Message } from '@/types/chat';

interface ChatInterfaceProps {
  className?: string;
}

// Message Component
const MessageBubble: React.FC<{ message: Message }> = ({ message }) => {
  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getRiskColor = (risk?: string) => {
    switch (risk) {
      case 'low': return 'text-green-400';
      case 'medium': return 'text-yellow-400';
      case 'high': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className={`chat-message ${message.role} animate-slide-up`}>
      <div className="flex items-start space-x-3">
        {/* Avatar */}
        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
          message.role === 'user' 
            ? 'bg-white text-black' 
            : 'bg-gray-700 text-white'
        }`}>
          {message.role === 'user' ? 'U' : 'AI'}
        </div>

        {/* Message Content */}
        <div className="flex-1 space-y-2">
          {/* Message Text */}
          <div className="text-white leading-relaxed">
            {message.isLoading ? (
              <div className="flex items-center space-x-2">
                <div className="loading-dots">
                  <div></div>
                  <div></div>
                  <div></div>
                </div>
                <span className="text-gray-400">Thinking...</span>
              </div>
            ) : (
              <div 
                dangerouslySetInnerHTML={{ 
                  __html: message.content.replace(/\n/g, '<br>') 
                }} 
              />
            )}
          </div>

          {/* Message Metadata */}
          {message.metadata && !message.isLoading && (
            <div className="flex flex-wrap gap-4 text-xs text-gray-400 pt-2">
              {message.metadata.confidence_score && (
                <span>
                  Confidence: {Math.round(message.metadata.confidence_score * 100)}%
                </span>
              )}
              {message.metadata.risk_assessment && (
                <span className={getRiskColor(message.metadata.risk_assessment.overall_risk)}>
                  Risk: {message.metadata.risk_assessment.overall_risk}
                </span>
              )}
              {message.metadata.processing_time && (
                <span>
                  {message.metadata.processing_time.toFixed(2)}s
                </span>
              )}
              {message.metadata.context_sources && message.metadata.context_sources.length > 0 && (
                <span>
                  Sources: {message.metadata.context_sources.length}
                </span>
              )}
            </div>
          )}

          {/* Error Display */}
          {message.error && (
            <div className="bg-red-900/20 border border-red-800 rounded-lg p-3 mt-2">
              <div className="flex items-center space-x-2 text-red-400 text-sm">
                <AlertCircle className="w-4 h-4" />
                <span>{message.error}</span>
              </div>
            </div>
          )}

          {/* Timestamp */}
          <div className="text-xs text-gray-500">
            {formatTime(message.timestamp)}
          </div>
        </div>
      </div>
    </div>
  );
};

// Main Chat Interface Component
export const ChatInterface: React.FC<ChatInterfaceProps> = ({ className = '' }) => {
  const {
    currentSession,
    isLoading,
    error,
    isConnected,
    sendMessage,
    clearError,
    retryLastMessage,
    isTyping,
    startNewConversation,
    exportCurrentSession,
    importSessionFromJson,
  } = useChat();

  const [inputValue, setInputValue] = useState('');
  const [location, setLocation] = useState('');
  const [streamingEnabled, setStreamingEnabled] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentSession?.messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!inputValue.trim() || isLoading) return;
    
    const message = inputValue.trim();
    setInputValue('');
    
    try {
      await sendMessage(message, { 
        location: location.trim() || undefined,
        streaming: streamingEnabled 
      });
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  // Handle key press for sending messages
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Handle export session
  const handleExport = () => {
    const sessionData = exportCurrentSession();
    if (sessionData) {
      const blob = new Blob([sessionData], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `chat-session-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  // Handle import session
  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target?.result as string;
        importSessionFromJson(content);
      };
      reader.readAsText(file);
    }
  };

  return (
    <div className={`flex flex-col h-full bg-black ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-800">
        <div>
          <h1 className="text-xl font-bold text-white">Jugaad Navigator</h1>
          <p className="text-sm text-gray-400">AI Administrative Assistant</p>
        </div>
        
        <div className="flex items-center space-x-2">
          {/* Connection Status */}
          <div className={`w-2 h-2 rounded-full ${
            isConnected ? 'bg-green-500' : 'bg-red-500'
          }`} />
          
          {/* Controls */}
          <button
            onClick={startNewConversation}
            className="btn-secondary"
            title="New Conversation"
          >
            New Chat
          </button>
          
          {currentSession && (
            <>
              <button
                onClick={handleExport}
                className="btn-secondary"
                title="Export Session"
              >
                <Download className="w-4 h-4" />
              </button>
              
              <button
                onClick={() => fileInputRef.current?.click()}
                className="btn-secondary"
                title="Import Session"
              >
                <Upload className="w-4 h-4" />
              </button>
              
              <input
                ref={fileInputRef}
                type="file"
                accept=".json"
                onChange={handleImport}
                className="hidden"
                aria-label="Import chat session from JSON file"
              />
            </>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-900/20 border-b border-red-800 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-red-400">
              <AlertCircle className="w-5 h-5" />
              <span>{error}</span>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={retryLastMessage}
                className="text-red-400 hover:text-red-300 flex items-center space-x-1"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Retry</span>
              </button>
              <button
                onClick={clearError}
                className="text-red-400 hover:text-red-300"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
        {currentSession?.messages.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 mb-4">
              <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                AI
              </div>
              <h3 className="text-lg font-medium text-white mb-2">
                Welcome to Jugaad Navigator
              </h3>
              <p className="max-w-md mx-auto">
                I'm here to help you navigate administrative challenges with creative, 
                practical solutions. Ask me anything about bureaucracy, documentation, 
                or everyday problems in India.
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto mt-8">
              {[
                "How can I deal with attendance shortage?",
                "What are the shortcuts for getting documents verified?",
                "Help me understand the RTI process",
                "How to handle bureaucratic delays?"
              ].map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => setInputValue(suggestion)}
                  className="text-left p-4 bg-gray-900 rounded-lg border border-gray-800 hover:border-gray-700 transition-colors"
                >
                  <span className="text-white">{suggestion}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          currentSession?.messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-800 p-4">
        {/* Settings Row */}
        <div className="flex flex-wrap gap-4 mb-3 text-sm">
          <div className="flex items-center space-x-2">
            <input
              type="text"
              placeholder="Location (optional)"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="input-field w-32"
            />
          </div>
          
          <label className="flex items-center space-x-2 text-gray-400">
            <input
              type="checkbox"
              checked={streamingEnabled}
              onChange={(e) => setStreamingEnabled(e.target.checked)}
              className="rounded"
              aria-label="Enable streaming responses"
            />
            <span>Stream responses</span>
          </label>
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="flex space-x-2">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={
                isConnected 
                  ? "Ask me anything about administrative challenges..." 
                  : "Reconnecting to server..."
              }
              disabled={!isConnected}
              className="input-field w-full resize-none"
              rows={1}
              style={{ minHeight: '44px' }}
            />
          </div>
          
          <button
            type="submit"
            disabled={!inputValue.trim() || isLoading || !isConnected}
            className="btn-primary px-6 flex items-center space-x-2"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            <span className="hidden sm:inline">Send</span>
          </button>
        </form>
        
        {isTyping() && (
          <div className="text-sm text-gray-400 mt-2 flex items-center space-x-2">
            <div className="loading-dots">
              <div></div>
              <div></div>
              <div></div>
            </div>
            <span>AI is thinking...</span>
          </div>
        )}
      </div>
    </div>
  );
};
'use client'

/**
 * Main Page Component
 * The primary chat interface page
 */

import React, { useEffect, useState } from 'react';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { useChat } from '@/hooks/useChat';
import { Loader2, Wifi, WifiOff, AlertTriangle, CheckCircle } from 'lucide-react';

export default function HomePage() {
  const { isConnected, checkConnection } = useChat();
  const [isInitializing, setIsInitializing] = useState(true);
  const [healthStatus, setHealthStatus] = useState<'checking' | 'healthy' | 'error'>('checking');

  // Initialize the application
  useEffect(() => {
    const initialize = async () => {
      try {
        await checkConnection();
        setHealthStatus('healthy');
      } catch (error) {
        console.error('Initialization failed:', error);
        setHealthStatus('error');
      } finally {
        setIsInitializing(false);
      }
    };

    initialize();
  }, [checkConnection]);

  // Show loading screen during initialization
  if (isInitializing) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto">
            <Loader2 className="w-8 h-8 text-white animate-spin" />
          </div>
          <div className="space-y-2">
            <h2 className="text-xl font-semibold text-white">Initializing Jugaad Navigator</h2>
            <p className="text-gray-400">Connecting to AI services...</p>
          </div>
        </div>
      </div>
    );
  }

  // Show error screen if initialization failed
  if (healthStatus === 'error') {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center space-y-6 max-w-md mx-auto p-8">
          <div className="w-16 h-16 bg-red-900 rounded-full flex items-center justify-center mx-auto">
            <AlertTriangle className="w-8 h-8 text-red-400" />
          </div>
          <div className="space-y-3">
            <h2 className="text-xl font-semibold text-white">Connection Failed</h2>
            <p className="text-gray-400">
              Unable to connect to the AI service. Please check if the backend server is running.
            </p>
            <div className="bg-gray-900 rounded-lg p-4 text-left">
              <p className="text-sm text-gray-300 font-mono">
                Expected backend URL: <br />
                <span className="text-white">http://127.0.0.1:8000</span>
              </p>
            </div>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="btn-primary"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black">
      {/* Status Bar */}
      <div className="bg-gray-900 px-4 py-2 border-b border-gray-800">
        <div className="flex items-center justify-between max-w-6xl mx-auto">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              {isConnected ? (
                <>
                  <Wifi className="w-4 h-4 text-green-400" />
                  <span className="text-sm text-green-400">Connected</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-4 h-4 text-red-400" />
                  <span className="text-sm text-red-400">Disconnected</span>
                </>
              )}
            </div>
            
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-4 h-4 text-green-400" />
              <span className="text-sm text-gray-300">AI Ready</span>
            </div>
          </div>
          
          <div className="text-sm text-gray-400">
            Powered by Advanced AI • Secure & Private
          </div>
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="h-[calc(100vh-48px)]">
        <div className="max-w-6xl mx-auto h-full">
          <ChatInterface className="h-full" />
        </div>
      </div>

      {/* Footer */}
      <div className="bg-gray-900 px-4 py-3 border-t border-gray-800 text-center">
        <div className="max-w-6xl mx-auto">
          <p className="text-xs text-gray-500">
            Jugaad Navigator - AI Administrative Assistant | 
            Built with Next.js & FastAPI | 
            <span className="text-gray-400"> Always prioritize legal and ethical solutions</span>
          </p>
        </div>
      </div>
    </div>
  );
}
/**
 * DUMB COMPONENT - Just renders UI and calls API functions
 * NO fetch, NO async logic, NO streaming logic
 * Just event handlers that call apiClient functions
 */

import React, { useState, useRef, useEffect } from 'react';
import { sendPrompt, streamPrompt, APIError, NetworkError } from '../api/apiClient';
import { Send } from 'lucide-react';
import MessageBubble from './MessageBubble';

const ChatInterface = ({ currentMode }) => {
    // UI state only - no async logic
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    // Ref to store current streaming abort function
    const abortStreamRef = useRef(null);

    // Auto-scroll to bottom ref
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    /**
     * Handle send button click
     * Just calls API function and updates UI state
     */
    const handleSend = async () => {
        if (!inputValue.trim() || isLoading) return;

        const userMessage = inputValue.trim();

        // Add user message to UI immediately
        setMessages(prev => [...prev, {
            role: 'user',
            content: userMessage,
            timestamp: Date.now(),
        }]);

        // Clear input
        setInputValue('');
        setIsLoading(true);
        setError(null);

        // Add placeholder for assistant message
        const assistantMessageId = Date.now();
        setMessages(prev => [...prev, {
            id: assistantMessageId,
            role: 'assistant',
            content: '',
            isStreaming: true,
            timestamp: assistantMessageId,
        }]);

        // Call API function (streaming)
        abortStreamRef.current = streamPrompt(
            userMessage,
            currentMode,

            // onToken callback - just update UI state
            // onToken callback - just update UI state
            (token, type) => {
                // NUCLEAR: Ignore thinking, check for leaks
                if (type === 'thinking') return;
                if (!token || typeof token !== 'string') return;

                // Final safety check
                if (token.includes('NUTRI-CHEM') || token.includes('capabilities')) return;

                setMessages(prev => prev.map(msg => {
                    if (msg.id !== assistantMessageId) return msg;

                    return {
                        ...msg,
                        content: (msg.content || '') + token
                    };
                }));
            },

            // onComplete callback
            (fullResponse) => {
                setMessages(prev => prev.map(msg =>
                    msg.id === assistantMessageId
                        ? { ...msg, isStreaming: false }
                        : msg
                ));
                setIsLoading(false);
            },

            // onError callback - just update UI state
            (error) => {
                setError(getErrorMessage(error));
                setIsLoading(false);

                // Remove streaming message on error
                setMessages(prev => prev.filter(msg => msg.id !== assistantMessageId));
            }
        );
    };

    /**
     * Handle stop button
     */
    const handleStop = () => {
        if (abortStreamRef.current) {
            abortStreamRef.current(); // Call abort function
            abortStreamRef.current = null;
        }
        setIsLoading(false);
    };

    /**
     * Handle Enter key
     */
    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    /**
     * Get user-friendly error message
     */
    const getErrorMessage = (error) => {
        if (error instanceof NetworkError) {
            return '🌐 Network error. Please check your connection.';
        }
        if (error instanceof APIError) {
            return `❌ ${error.message}`;
        }
        return '❌ Something went wrong. Please try again.';
    };

    return (
        <div className="flex flex-col h-full">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-3 sm:p-6 space-y-4 sm:space-y-6">
                {messages
                    .filter(msg => {
                        // FILTER: Remove messages with "NUTRI-CHEM GPT" or duplicates if needed
                        if (msg.role === 'system') return false;

                        // Check for system prompt indicators
                        const content = msg.content || '';
                        if (typeof content === 'string' && (
                            content.includes("NUTRI-CHEM GPT") ||
                            content.includes("I am designed to provide") ||
                            content.startsWith("System Prompt:")
                        )) {
                            console.warn("Filtered system prompt from UI");
                            return false;
                        }

                        return true;
                    })
                    .map((msg, idx) => (
                        <div
                            key={msg.id || idx}
                            className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} gap-1`}
                        >
                            {/* Message Bubble */}
                            {(msg.content || (msg.role === 'assistant' && msg.isStreaming)) && (
                                <MessageBubble
                                    role={msg.role}
                                    content={msg.content}
                                    isStreaming={msg.isStreaming}
                                />
                            )}
                        </div>
                    ))}

                {/* Error message */}
                {error && (
                    <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-xl max-w-3xl mx-auto shadow-sm">
                        {error}
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            <div className="p-3 sm:p-6 border-t border-orange-200/30 dark:border-orange-400/20 bg-white/20 dark:bg-black/20 backdrop-blur-lg safe-bottom">
                <div className="flex gap-2 sm:gap-3 items-end max-w-4xl mx-auto">
                    <textarea
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="What would you like to cook today?"
                        rows={1}
                        className="flex-1 px-3 py-2.5 sm:px-4 sm:py-3 text-sm sm:text-base rounded-xl border-0 focus:outline-none bg-gradient-to-br from-white/40 via-gray-100/50 to-orange-100/60 dark:from-black/80 dark:via-gray-900/70 dark:to-orange-950/60 dark:text-white backdrop-blur-xl resize-none placeholder:text-gray-600/70 dark:placeholder:text-gray-300/60 transition-all duration-300"
                    />

                    {isLoading ? (
                        <button
                            onClick={handleStop}
                            className="px-4 sm:px-6 py-2.5 sm:py-3 bg-red-500/90 hover:bg-red-600 text-white text-sm sm:text-base rounded-xl font-semibold transition-colors backdrop-blur-sm whitespace-nowrap"
                        >
                            Stop
                        </button>
                    ) : (
                        <button
                            onClick={handleSend}
                            disabled={!inputValue.trim()}
                            className="px-4 sm:px-6 py-2.5 sm:py-3 bg-gradient-to-r from-orange-400 to-orange-500 hover:from-orange-500 hover:to-orange-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm sm:text-base rounded-xl font-semibold transition-all backdrop-blur-sm whitespace-nowrap flex items-center gap-2"
                        >
                            <Send className="w-4 h-4 sm:w-5 sm:h-5" />
                            <span className="hidden sm:inline">Cook!</span>
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ChatInterface;
/**
 * DUMB COMPONENT - Just renders UI and calls API functions
 * NO fetch, NO async logic, NO streaming logic
 * Just event handlers that call apiClient functions
 */

import React, { useState, useRef, useEffect } from 'react';
import { streamNutriChat, APIError, NetworkError, TimeoutError } from '../api/apiClient';
import { Send } from 'lucide-react';
import MessageBubble from './MessageBubble';
import ErrorPanel from './ErrorPanel';

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
            phase: null, // Track the current Nutri phase
            timestamp: assistantMessageId,
        }]);

        // Call Unified Nutri API function (Phase 13 Integration)
        abortStreamRef.current = streamNutriChat(
            userMessage,
            { verbosity: 'medium', explanations: true, streaming: true },

            // onPhase callback
            (phaseData) => {
                setMessages(prev => prev.map(msg =>
                    msg.id === assistantMessageId
                        ? { ...msg, phase: phaseData }
                        : msg
                ));
            },

            // onComplete callback
            (finalOutput) => {
                const finalContent = `### ${finalOutput.recipe?.slice(0, 100) || 'Optimized Recipe'}\n\n${finalOutput.explanation}\n\n**Scientific Summary:** ${finalOutput.sensory_profile ? 'Sensory balance achieved.' : 'Standard synthesis complete.'}`;

                setMessages(prev => prev.map(msg =>
                    msg.id === assistantMessageId
                        ? {
                            ...msg,
                            content: finalContent,
                            isStreaming: false,
                            phase: null
                        }
                        : msg
                ));
                setIsLoading(false);
            },

            // onError callback
            (err) => {
                setError({
                    type: err.name || 'Error',
                    status: err.status || (err instanceof NetworkError ? 'NETWORK_FAIL' : 'UNKNOWN'),
                    message: err.message || 'An unexpected error occurred',
                });
                setIsLoading(false);
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
                                    isWarmingUp={msg.isWarmingUp}
                                    phase={msg.phase}
                                />
                            )}
                        </div>
                    ))}

                {/* Detailed Error Panel */}
                {error && (
                    <ErrorPanel
                        error={error}
                        onDismiss={() => setError(null)}
                    />
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
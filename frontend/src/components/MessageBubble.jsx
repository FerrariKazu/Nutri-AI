import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const MessageBubble = ({ role, content, isStreaming, isWarmingUp, phase }) => {
    // Styling for User vs Assistant
    const isUser = role === 'user';
    const alignClass = isUser ? 'items-end' : 'items-start';
    const bgClass = isUser
        ? 'bg-orange-500 text-white'
        : 'bg-white/90 backdrop-blur-sm border border-gray-200 dark:bg-black/60 dark:border-gray-800 dark:text-gray-100';
    const maxWidth = 'max-w-3xl w-full sm:w-auto';

    // Markdown components customization
    const components = {
        h1: ({ node, ...props }) => <h1 className="text-lg sm:text-xl font-bold mb-2 mt-4" {...props} />,
        h2: ({ node, ...props }) => <h2 className="text-md sm:text-lg font-bold mb-2 mt-3" {...props} />,
        h3: ({ node, ...props }) => <h3 className="text-sm sm:text-md font-bold mb-1 mt-2" {...props} />,
        ul: ({ node, ...props }) => <ul className="list-disc pl-4 sm:pl-5 mb-2 space-y-1 text-sm sm:text-base" {...props} />,
        ol: ({ node, ...props }) => <ol className="list-decimal pl-4 sm:pl-5 mb-2 space-y-1 text-sm sm:text-base" {...props} />,
        code: ({ node, inline, className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || '');
            return !inline ? (
                <div className="rounded-md bg-gray-100 dark:bg-gray-900 p-2 sm:p-3 my-2 overflow-x-auto text-xs sm:text-sm">
                    <code className={className} {...props}>
                        {children}
                    </code>
                </div>
            ) : (
                <code className="bg-gray-100 dark:bg-gray-800 rounded px-1 py-0.5 text-xs sm:text-sm font-mono text-gray-800 dark:text-gray-200" {...props}>
                    {children}
                </code>
            );
        },
        a: ({ node, ...props }) => <a className="text-blue-500 hover:underline break-words" target="_blank" rel="noopener noreferrer" {...props} />,
        p: ({ node, ...props }) => <p className="mb-2 last:mb-0 leading-relaxed break-words text-sm sm:text-base" {...props} />,
    };

    return (
        <div className={`flex flex-col ${alignClass} gap-1 w-full`}>
            <div
                className={`
                    ${maxWidth} rounded-xl p-3 sm:p-4 
                    ${bgClass} 
                    shadow-sm overflow-hidden break-words
                `}
            >
                {/* Phase Status Indicator */}
                {isStreaming && phase && phase.message && phase.message.trim() && (
                    <div className="flex items-center gap-2 mb-2 p-2 rounded-lg bg-orange-100/50 dark:bg-orange-950/30 border border-orange-200/50 dark:border-orange-400/20">
                        <div className="flex space-x-1 items-center">
                            <div className="w-1.5 h-1.5 bg-orange-500 rounded-full animate-pulse"></div>
                        </div>
                        <div className="text-xs font-semibold text-orange-800 dark:text-orange-300 uppercase tracking-tight">
                            PHASE {phase.phase}: {phase.message}
                        </div>
                    </div>
                )}

                {/* Streaming Indicator if empty content and no phase */}
                {isStreaming && !content && !phase && role === 'assistant' && (
                    <div className="flex space-x-1 items-center h-6">
                        <div className="w-2 h-2 bg-orange-500/50 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                        <div className="w-2 h-2 bg-orange-500/50 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                        <div className="w-2 h-2 bg-orange-500/50 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                )}

                {/* Content */}
                {content && typeof content === 'string' && (
                    <div className={`prose prose-sm dark:prose-invert max-w-none ${!isUser ? 'font-serif' : ''} ${isWarmingUp ? 'italic opacity-70 animate-pulse' : ''}`}>
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={components}
                        >
                            {content}
                        </ReactMarkdown>
                    </div>
                )}

                {/* Cursor */}
                {isStreaming && content && role === 'assistant' && (
                    <span className="inline-block w-1.5 h-4 bg-orange-500/50 animate-pulse ml-1 align-middle" />
                )}
            </div>
        </div>
    );
};

export default MessageBubble;
import React, { useState } from 'react';

const ThinkingIndicator = ({ content, isStreaming }) => {
    // Styling for minimal impact
    const [isExpanded, setIsExpanded] = useState(false);

    if (!content && !isStreaming) return null;

    return (
        <div className="max-w-3xl w-full mb-2">
            <details
                className="group"
                open={isExpanded}
                onToggle={(e) => setIsExpanded(e.target.open)}
            >
                <summary className="cursor-pointer text-xs font-mono text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 flex items-center gap-2 mb-2 select-none transition-colors border-b border-transparent hover:border-gray-200 dark:hover:border-gray-700 pb-1 w-fit">
                    {/* Improved spinner/icon */}
                    <div className={`w-3.5 h-3.5 rounded-full bg-kitchen-cinnamon/10 dark:bg-kitchen-cinnamon/20 flex items-center justify-center border border-kitchen-cinnamon/30 ${isStreaming ? 'animate-pulse' : ''}`}>
                        <div className={`w-1.5 h-1.5 rounded-full bg-kitchen-cinnamon ${isStreaming ? 'animate-ping' : ''}`} />
                    </div>

                    <span className="opacity-80 font-medium tracking-wide">
                        {isStreaming ? 'Thinking Process...' : 'View Reasoning'}
                    </span>

                    {/* Chevron */}
                    <div className="text-[10px] transform transition-transform duration-200 group-open:rotate-90 text-gray-400 ml-1">
                        ▶
                    </div>
                </summary>

                <div className="pl-4 border-l-2 border-gray-200 dark:border-gray-800 ml-1.5 my-2 animate-in fade-in slide-in-from-top-1 duration-200">
                    <p className="text-xs font-mono text-gray-600 dark:text-gray-400 whitespace-pre-wrap leading-relaxed bg-gray-50 dark:bg-gray-900/50 p-3 rounded-lg border border-gray-100 dark:border-gray-800">
                        {content || (
                            <span className="italic opacity-50">Initializing thought process...</span>
                        )}
                        {isStreaming && (
                            <span className="inline-block w-1.5 h-3 bg-gray-400/50 animate-pulse ml-1 align-middle" />
                        )}
                    </p>
                </div>
            </details>
        </div>
    );
};

export default ThinkingIndicator;

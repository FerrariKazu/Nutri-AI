import React, { useState, useRef, useEffect } from 'react';
import { Terminal, Send, ShieldCheck, Cpu } from 'lucide-react';

/**
 * ReasoningConsole - System-like query entry.
 * Replaces traditional chat bubbles with a command console feel.
 */
const ReasoningConsole = ({ onSend, isLoading, isMemoryActive }) => {
    const [inputValue, setInputValue] = useState('');
    const textareaRef = useRef(null);

    const handleSend = () => {
        if (!inputValue.trim() || isLoading) return;
        onSend(inputValue.trim());
        setInputValue('');
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
        }
    }, [inputValue]);

    return (
        <div className="p-6 bg-neutral-950 border-t border-neutral-800">
            <div className="max-w-4xl mx-auto flex flex-col gap-3">
                {/* Meta Indicators */}
                <div className="flex items-center gap-4 px-1">
                    <div className="flex items-center gap-1.5 grayscale opacity-50">
                        <Cpu className={`w-3 h-3 ${isLoading ? 'text-accent animate-pulse-subtle' : ''}`} />
                        <span className="text-[10px] font-mono uppercase tracking-widest">
                            Processor: {isLoading ? 'Active' : 'Idle'}
                        </span>
                    </div>
                    <div className={`flex items-center gap-1.5 transition-opacity ${isMemoryActive ? 'opacity-50' : 'opacity-20'}`}>
                        <ShieldCheck className="w-3 h-3 text-accent" />
                        <span className="text-[10px] font-mono uppercase tracking-widest">
                            Memory: Contextual
                        </span>
                    </div>
                </div>

                {/* Input Surface */}
                <div className="relative group">
                    <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                        <Terminal className="w-4 h-4 text-neutral-600 group-focus-within:text-accent/50 transition-colors" />
                    </div>
                    <textarea
                        ref={textareaRef}
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Describe the dish, constraint, or scientific question..."
                        rows={1}
                        className="w-full bg-neutral-900 border border-neutral-800 rounded-lg pl-12 pr-12 py-3.5 text-sm font-sans focus:outline-none focus:border-neutral-600 transition-all placeholder:text-neutral-600 resize-none leading-relaxed"
                    />
                    <button
                        onClick={handleSend}
                        disabled={!inputValue.trim() || isLoading}
                        className={`
                            absolute right-2.5 top-1/2 -translate-y-1/2 p-1.5 rounded-md transition-all
                            ${!inputValue.trim() || isLoading
                                ? 'text-neutral-700'
                                : 'text-accent hover:bg-accent/10'}
                        `}
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ReasoningConsole;

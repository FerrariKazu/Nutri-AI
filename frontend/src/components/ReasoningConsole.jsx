import React, { useState, useRef, useEffect } from 'react';
import { Terminal, Send, ShieldCheck, Cpu } from 'lucide-react';

/**
 * ReasoningConsole - System-like query entry.
 * Replaces traditional chat bubbles with a command console feel.
 */
const ReasoningConsole = ({ onSend, isLoading, isMemoryActive, setInputValue: externalSetInputValue }) => {
    const [inputValue, setInputValue] = useState('');
    const [isSending, setIsSending] = useState(false);
    const textareaRef = useRef(null);

    // Expose input setter for external control (starter prompts)
    useEffect(() => {
        if (externalSetInputValue) {
            externalSetInputValue((text) => {
                setInputValue(text);
                setTimeout(() => textareaRef.current?.focus(), 100);
            });
        }
    }, [externalSetInputValue]);

    const handleSend = async () => {
        if (!inputValue.trim() || isLoading || isSending) return;

        setIsSending(true);
        onSend(inputValue.trim());
        setInputValue('');

        // Prevent double-tap for 500ms
        setTimeout(() => setIsSending(false), 500);
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
        <div className="p-3 md:p-6 bg-neutral-950/80 border-t border-neutral-800 backdrop-blur-none safe-bottom">
            <div className="max-w-4xl mx-auto flex flex-col gap-2 md:gap-3">
                {/* Meta Indicators */}
                <div className="flex items-center gap-3 md:gap-4 px-1">
                    <div className="flex items-center gap-1.5 grayscale opacity-50">
                        <Cpu className={`w-3 h-3 ${isLoading ? 'text-accent animate-pulse-subtle' : ''}`} />
                        <span className="text-[10px] font-mono uppercase tracking-widest hidden sm:inline">
                            Processor: {isLoading ? 'Active' : 'Idle'}
                        </span>
                        <span className="text-[10px] font-mono uppercase tracking-widest sm:hidden">
                            {isLoading ? 'Active' : 'Idle'}
                        </span>
                    </div>
                    <div className={`flex items-center gap-1.5 transition-opacity ${isMemoryActive ? 'opacity-50' : 'opacity-20'}`}>
                        <ShieldCheck className="w-3 h-3 text-accent" />
                        <span className="text-[10px] font-mono uppercase tracking-widest hidden sm:inline">
                            Memory: Contextual
                        </span>
                    </div>
                </div>

                {/* Input Surface */}
                <div className="relative group">
                    <div className="absolute inset-y-0 left-3 md:left-4 flex items-center pointer-events-none">
                        <Terminal className="w-4 h-4 text-neutral-600 group-focus-within:text-accent/50 transition-colors" />
                    </div>
                    <textarea
                        ref={textareaRef}
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={isLoading}
                        placeholder="Describe the dish, constraint, or scientific question..."
                        rows={1}
                        className={`w-full bg-neutral-900 border border-neutral-800 rounded-lg pl-10 md:pl-12 pr-14 md:pr-12 py-3 md:py-3.5 min-h-[48px] text-sm md:text-base font-sans focus:outline-none focus:border-neutral-600 transition-all placeholder:text-neutral-600 resize-none leading-relaxed ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    />
                    <button
                        onClick={handleSend}
                        disabled={!inputValue.trim() || isLoading || isSending}
                        className={`
                            absolute right-2 top-1/2 -translate-y-1/2 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-md transition-all active:scale-95
                            ${!inputValue.trim() || isLoading || isSending
                                ? 'text-neutral-700'
                                : 'text-accent hover:bg-accent/10'}
                        `}
                    >
                        <Send className="w-5 h-5" />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ReasoningConsole;

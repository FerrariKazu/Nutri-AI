import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronDown, ChevronRight, Binary, Fingerprint, ShieldCheck, Hash, Activity, Book, FileText, AlertTriangle, Info } from 'lucide-react';
import StarterPrompts from './StarterPrompts';
import NutriIntelligencePanel from './IntelligenceTransparency/NutriIntelligencePanel';
import { adaptExecutionTrace } from '../utils/traceAdapter';

/**
 * PhaseStream - Collapsible, phase-aware reasoning output.
 * Renders the deterministic lineage of Nutri's internal steps.
 * 
 * HARDENING:
 * - Smart Scroll: Only auto-scrolls if user was already at bottom.
 * - Forced Scroll: On hydration or DONE state.
 * - Starter Prompts: Show only when zero user messages.
 */
const PhaseStream = ({ messages, streamStatus, onPromptSelect }) => {
    const scrollRef = useRef(null);
    const [isAtBottom, setIsAtBottom] = useState(true);

    // Lifecycle: Check if we are in an empty state
    const isEmptyState = messages.length === 0;

    // Scroll Handler
    const handleScroll = () => {
        if (!scrollRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
        const atBottom = scrollHeight - scrollTop - clientHeight < 50; // 50px threshold
        setIsAtBottom(atBottom);
    };

    // Auto-Scroll Effect
    useEffect(() => {
        if (!scrollRef.current) return;

        // Force scroll scenarios
        const forceScroll = streamStatus === 'DONE' || streamStatus === 'HYDRATING';

        if (isAtBottom || forceScroll) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, streamStatus, isAtBottom]);

    return (
        <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto p-4 md:p-8 space-y-8 md:space-y-12 relative scroll-smooth"
        >
            {/* 1. Hero / Landing State (Rendered ONLY when messages.length === 0) */}
            {isEmptyState ? (
                <div className="nutri-hero flex flex-col items-center justify-center min-h-[60vh] relative z-10">
                    {/* Centered Brand Logo */}
                    <img
                        src="/nutri-logo.png"
                        alt="Nutri Logo"
                        className="nutri-hero-logo"
                    />

                    {/* Scientific Slogan */}
                    <p className="nutri-hero-slogan text-xs md:text-sm text-neutral-500 font-mono tracking-[0.2em] max-w-2xl text-center px-4 uppercase opacity-80">
                        Culinary data modeled as physical systems.
                    </p>

                    {/* Suggestion Cards */}
                    <div className="nutri-hero-cards w-full mt-4 md:mt-8">
                        <StarterPrompts onSelectPrompt={onPromptSelect} />
                    </div>
                </div>
            ) : (
                /* 2. Conversation Stream */
                messages.map((msg, idx) => (
                    <div key={idx} className="max-w-4xl mx-auto flex flex-col gap-6 animate-fade-in">
                        {/* User Query - Minimalist Header */}
                        {msg.role === 'user' && (
                            <div className="flex items-start gap-4 py-4 border-b border-neutral-800/50">
                                <Fingerprint className="w-5 h-5 text-neutral-600 shrink-0" />
                                <h2 className="text-xl font-serif text-neutral-400 font-normal leading-tight">
                                    {msg.content}
                                </h2>
                            </div>
                        )}

                        {/* System Message - Visually Subordinate Footer */}
                        {msg.role === 'system' && (
                            <div className="flex flex-col items-center justify-center py-4 md:py-6 gap-2 opacity-50 animate-fade-in">
                                <div className="h-px w-12 bg-neutral-800"></div>
                                <span className="text-xs text-neutral-600 font-mono uppercase tracking-wider text-center px-4">
                                    {msg.content}
                                </span>
                            </div>
                        )}

                        {/* Assistant Response - Phase Container */}
                        {msg.role === 'assistant' && (
                            <div className="flex flex-col gap-4 py-2 md:py-4">
                                {/* Thinking Indicator (STREAMING state, no content yet) */}
                                {msg.isStreaming && !msg.content && (!msg.phases || msg.phases.length === 0) && (
                                    <div className="flex items-center gap-2 text-neutral-500 animate-pulse">
                                        <div className="flex gap-1">
                                            <span className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                                            <span className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                                            <span className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                                        </div>
                                        <span className="text-xs font-mono uppercase tracking-wider">
                                            Nutri is thinking...
                                        </span>
                                    </div>
                                )}

                                {/* Intermediate Phases (if streaming) */}
                                {msg.phases && msg.phases.map((phase) => (
                                    <details
                                        key={phase.phase}
                                        className="group border-l border-neutral-800 ml-2 pl-4"
                                    >
                                        <summary className="list-none cursor-pointer flex items-center gap-2 py-1 select-none">
                                            <ChevronRight className="w-3 h-3 text-neutral-600 group-open:rotate-90 transition-transform" />
                                            <span className="text-[10px] font-mono uppercase tracking-widest text-neutral-500 group-hover:text-neutral-300 transition-colors">
                                                Phase {phase.phase} — {phase.title}
                                            </span>
                                        </summary>
                                        <div className="py-2 text-xs text-neutral-400 font-sans leading-relaxed">
                                            {phase.partial_output}
                                        </div>
                                    </details>
                                ))}

                                {/* Final Output */}
                                {msg.content && (
                                    <div className="prose prose-neutral prose-invert max-w-none font-serif text-lg leading-relaxed text-neutral-200">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {msg.content}
                                        </ReactMarkdown>
                                    </div>
                                )}

                                {/* Live Status Message - NEW */}
                                {msg.isStreaming && msg.statusMessage && (
                                    <div className="flex items-center gap-3 ml-2 py-2 px-4 bg-accent/5 border-l-2 border-accent/40 rounded-r animate-fade-in">
                                        <Binary className="w-4 h-4 text-accent animate-pulse" />
                                        <span className="text-sm font-mono text-accent/90">
                                            {msg.statusMessage}
                                        </span>
                                    </div>
                                )}

                                {/* Minimal Pulse Indicator (if streaming content but no status message) */}
                                {msg.isStreaming && !msg.statusMessage && (
                                    <div className="flex items-center gap-1.5 ml-2 mt-2 opacity-50">
                                        <div className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce delay-200"></div>
                                    </div>
                                )}

                                {/* 🧠 Intelligence Transparency Panel (MANDATE: Always Mounted) */}
                                {(() => {
                                    const adapted = msg.executionTrace ? adaptExecutionTrace(msg.executionTrace) : null;
                                    return (
                                        <NutriIntelligencePanel uiTrace={adapted} />
                                    );
                                })()}

                                {/* Coming Soon: Regenerate */}
                                {!msg.isStreaming && msg.content && (
                                    <div className="pl-0 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button disabled className="text-[10px] text-neutral-700 font-mono uppercase tracking-widest cursor-not-allowed hover:text-neutral-600">
                                            Regenerate Response (Soon)
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                ))}
        </div>
    );
};

export default PhaseStream;

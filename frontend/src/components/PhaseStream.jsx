import React, { useState, useEffect, useRef, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronDown, ChevronRight, Binary, Fingerprint, ShieldCheck, Hash, Activity, Book, FileText, AlertTriangle, Info } from 'lucide-react';
import StarterPrompts from './StarterPrompts';
import NutriIntelligencePanel from './IntelligenceTransparency/NutriIntelligencePanel';
import MemoryInsight from './MemoryInsight';
import { adaptExecutionTrace } from '../utils/traceAdapter';
import { SUGGESTION_POOL } from '../api/suggestions';
import { getUserId } from '../utils/memoryManager';
import ResponseFormatter from './ResponseFormatter';

/**
 * hashString - Simple DJB2 hash for deterministic seeding.
 */
function hashString(str) {
    let hash = 5381;
    for (let i = 0; i < str.length; i++) {
        hash = (hash * 33) ^ str.charCodeAt(i);
    }
    return hash >>> 0;
}

/**
 * seededShuffle - Deterministic Fisher-Yates using LCG.
 */
function seededShuffle(array, seed) {
    const shuffled = [...array];
    let currentSeed = seed;

    const nextRandom = () => {
        currentSeed = (currentSeed * 1664525 + 1013904223) % 4294967296;
        return currentSeed / 4294967296;
    };

    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(nextRandom() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

/**
 * PhaseStream - Collapsible, phase-aware reasoning output.
 */
const PhaseStream = ({ messages, streamStatus, memoryInsight, onDismissInsight, onPromptSelect }) => {
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

    // Daily Rotating Suggestions Logic
    const dailySuggestions = useMemo(() => {
        // Step 1: Identity Extraction (Robust fallback to prevent NaN/Undefined seeds)
        const userId = getUserId() || 'anonymous';

        // Step 2: Temporal Seed (UTC Date)
        const today = new Date().toISOString().slice(0, 10);

        // Step 3: Combined Deterministic Seed
        const seedValue = today + userId;
        const seed = hashString(seedValue);

        console.log(`[SUGGESTIONS] Seeding with: "${seedValue}" (hash: ${seed})`);

        // Step 4: Shuffled Selection
        const shuffled = seededShuffle(SUGGESTION_POOL, seed);

        // Step 5: Diversified Take (1 Diagnostic, 1 Procedural, 1 Scientific)
        // For now, just take top 3 as requested, but ensure it's reactive.
        return shuffled.slice(0, 3);
    }, [messages.length, streamStatus]); // Re-evaluate when session state changes

    return (
        <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="messages-container flex-1 overflow-y-auto overflow-x-hidden px-4 py-4 md:px-8 md:py-6 space-y-8 md:space-y-12 relative scroll-smooth"
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
                        <StarterPrompts
                            prompts={dailySuggestions}
                            onSelectPrompt={onPromptSelect}
                        />
                    </div>
                </div>
            ) : (
                /* 2. Conversation Stream */
                messages.map((msg, idx) => (
                    <div key={idx} className="max-w-full sm:max-w-4xl mx-auto flex flex-col gap-4 sm:gap-6 animate-fade-in w-full text-[14px] sm:text-[16px]">
                        {/* User Query - Minimalist Header */}
                        {msg.role === 'user' && (
                            <div className="flex flex-col gap-2 py-3 sm:py-4 border-b border-neutral-800/50">
                                <div className="flex items-start gap-3 sm:gap-4">
                                    <Fingerprint className="w-4 h-4 sm:w-5 sm:h-5 text-neutral-600 shrink-0 mt-1" />
                                    <h2 className="text-lg sm:text-xl font-serif text-neutral-400 font-normal leading-tight break-words overflow-hidden" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                                        {msg.content}
                                    </h2>
                                </div>
                                {msg.image && (
                                    <div className="ml-7 sm:ml-9 mt-2 animate-fade-in group/userimg relative max-w-sm">
                                        <img 
                                            src={msg.image} 
                                            alt="User uploaded analysis target" 
                                            className="rounded-lg border border-neutral-800 shadow-xl ring-1 ring-white/5 object-cover max-h-48 cursor-zoom-in hover:brightness-110 transition-all"
                                        />
                                        <div className="absolute top-2 left-2 bg-neutral-950/60 backdrop-blur-md px-1.5 py-0.5 rounded text-[8px] font-mono text-neutral-400 uppercase tracking-tighter opacity-0 group-hover/userimg:opacity-100 transition-opacity">
                                            Visual Input Attached
                                        </div>
                                    </div>
                                )}
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
                                    <div className="w-full break-words" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                                        <ResponseFormatter text={msg.content} isStreaming={msg.isStreaming} />
                                    </div>
                                )}

                                {/* Live Status Message - NEW */}
                                {msg.isStreaming && msg.statusMessage && (() => {
                                    const STATUS_LABELS = {
                                        'reasoning': 'PROCESSOR: REASONING',
                                        'intent_check': 'PROCESSOR: ANALYZING INTENT',
                                        'mechanistic_analysis': 'PROCESSOR: CAUSAL MAPPING'
                                    };
                                    const displayStatus = STATUS_LABELS[msg.statusMessage] || msg.statusMessage;
                                    
                                    return (
                                        <div className="flex items-center gap-3 ml-2 py-2 px-4 bg-accent/5 border-l-2 border-accent/40 rounded-r animate-fade-in">
                                            <Binary className="w-4 h-4 text-accent animate-pulse" />
                                            <span className="text-sm font-mono text-accent/90">
                                                {displayStatus}
                                            </span>
                                        </div>
                                    );
                                })()}

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
                ))
            )}

            {/* Memory Insight Card (STC-005) — Rendered after all messages */}
            {!isEmptyState && (
                <MemoryInsight
                    insight={memoryInsight}
                    onDismiss={onDismissInsight}
                />
            )}
        </div>
    );
};

export default PhaseStream;

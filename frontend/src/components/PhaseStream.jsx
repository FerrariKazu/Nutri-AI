import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronDown, ChevronRight, Binary, Fingerprint, ShieldCheck, Hash, Activity, Book, FileText, AlertTriangle, Info } from 'lucide-react';
import StarterPrompts from './StarterPrompts';

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

    // Lifecycle: Count user messages
    const userMessageCount = messages.filter(m => m.role === 'user').length;

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
            {/* Idle-State: Identity Statement + Starter Prompts (LIFECYCLE RULE: userMessageCount === 0) */}
            {userMessageCount === 0 && (
                <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 md:gap-8">
                    {/* Identity Statement */}
                    <p className="text-xs md:text-sm text-neutral-600 font-mono tracking-wide max-w-2xl text-center px-4 uppercase opacity-60">
                        Nutri models culinary data as physical systems.
                    </p>

                    {/* Starter Prompts */}
                    <StarterPrompts onSelectPrompt={onPromptSelect} />
                </div>
            )}

            {messages.map((msg, idx) => (
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

                            {/* 🥗 Tier 1 Intelligence Report (Hardened Verification) */}
                            {msg.nutritionVerification && (
                                <div className="mt-8 space-y-6 animate-fade-in group/v">
                                    {/* Header: Overall Confidence & Summary */}
                                    <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-neutral-900/50 border border-neutral-800">
                                        <div className="flex items-center gap-3">
                                            <div className={`p-2 rounded-lg ${msg.nutritionVerification.final_confidence >= 0.7 ? 'bg-green-500/20' : 'bg-amber-500/20'}`}>
                                                <ShieldCheck className={`w-5 h-5 ${msg.nutritionVerification.final_confidence >= 0.7 ? 'text-green-400' : 'text-amber-400'}`} />
                                            </div>
                                            <div>
                                                <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-300">
                                                    Nutrition Intelligence Verified
                                                </h3>
                                                <p className="text-[10px] text-neutral-500 font-mono">
                                                    PROOF: {msg.nutritionVerification.proof_hash}
                                                </p>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-4">
                                            <div className="text-right">
                                                <div className="text-xl font-mono font-bold text-neutral-200">
                                                    {(msg.nutritionVerification.final_confidence * 100).toFixed(0)}%
                                                </div>
                                                <div className="text-[10px] text-neutral-500 uppercase tracking-tighter">
                                                    CONFIDENCE
                                                </div>
                                            </div>
                                            {msg.nutritionVerification.conflicts_detected && (
                                                <div className="p-2 rounded-full bg-amber-500/10 text-amber-500" title="Conflicting sources detected; higher-priority evidence used">
                                                    <AlertTriangle className="w-4 h-4" />
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Claim Cards Grid */}
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {msg.nutritionVerification.claims && msg.nutritionVerification.claims.map((claim, cidx) => (
                                            <div key={claim.claim_id || cidx} className="p-3 rounded-lg bg-neutral-900/30 border border-neutral-800/50 hover:border-neutral-700 transition-colors flex flex-col gap-2">
                                                <div className="flex items-start justify-between">
                                                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-tighter ${claim.status_label === 'Verified' ? 'bg-green-500/10 text-green-500' :
                                                        claim.status_label.includes('Supporting') ? 'bg-amber-500/10 text-amber-500' :
                                                            'bg-neutral-800 text-neutral-500'
                                                        }`}>
                                                        {claim.status_label === 'Verified' ? '✅ Verified' :
                                                            claim.status_label.includes('Supporting') ? '🟡 Supporting' : '⚪ Info'}
                                                    </span>
                                                    <div className="flex items-center gap-1 opacity-40 group-hover:opacity-100 transition-opacity">
                                                        {claim.source === 'pubchem' && <ShieldCheck className="w-3 h-3 text-green-400" />}
                                                        {claim.source === 'usda' && <Book className="w-3 h-3 text-blue-400" />}
                                                        {claim.source === 'peer_reviewed_rag' && <FileText className="w-3 h-3 text-purple-400" />}
                                                        <span className="text-[9px] font-mono text-neutral-500 uppercase">{claim.source}</span>
                                                    </div>
                                                </div>
                                                <p className="text-xs text-neutral-300 leading-snug">
                                                    {claim.text}
                                                </p>
                                                {claim.explanation && (
                                                    <p className="text-[9px] text-neutral-600 italic">
                                                        {claim.explanation}
                                                    </p>
                                                )}
                                                {claim.claim_id === msg.nutritionVerification.weakest_link_id && (
                                                    <div className="mt-1 flex items-center gap-1 text-[8px] text-amber-500/60 font-mono uppercase">
                                                        <Activity className="w-2 h-2" />
                                                        Weakest Link
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>

                                    {/* Uncertainty Accordion */}
                                    <details className="group p-3 rounded-lg bg-neutral-900/20 border border-neutral-800/30">
                                        <summary className="list-none cursor-pointer flex items-center justify-between font-mono text-[10px] text-neutral-500 uppercase tracking-widest hover:text-neutral-300 transition-colors">
                                            <div className="flex items-center gap-2">
                                                <Info className="w-3 h-3" />
                                                What affects this confidence?
                                            </div>
                                            <ChevronRight className="w-3 h-3 group-open:rotate-90 transition-transform" />
                                        </summary>
                                        <div className="mt-4 space-y-3">
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                {msg.nutritionVerification.variance_drivers && Object.entries(msg.nutritionVerification.variance_drivers).map(([driver, penalty]) => (
                                                    <div key={driver} className="flex items-center justify-between text-[11px] text-neutral-400">
                                                        <span className="capitalize">{driver.replace(/_/g, ' ')}</span>
                                                        <span className="text-orange-500/70 font-mono">-{Math.round(penalty * 100)}%</span>
                                                    </div>
                                                ))}
                                            </div>
                                            <div className="pt-2 border-t border-neutral-800/50">
                                                <p className="text-xs text-neutral-500 italic">
                                                    {msg.nutritionVerification.uncertainty_explanation || "Our confidence score measures potential variance in nutritional outcomes based on measurable evidence gaps."}
                                                </p>
                                            </div>
                                        </div>
                                    </details>

                                    {/* All Unverified Banner */}
                                    {msg.nutritionVerification.final_confidence < 0.4 && (
                                        <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/20 text-center">
                                            <p className="text-[11px] text-amber-500/80 font-medium italic">
                                                This answer contains informational content without verified nutrition data.
                                            </p>
                                        </div>
                                    )}
                                </div>
                            )}

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

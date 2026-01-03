import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronDown, ChevronRight, Binary, Fingerprint } from 'lucide-react';

/**
 * PhaseStream - Collapsible, phase-aware reasoning output.
 * Renders the deterministic lineage of Nutri's internal steps.
 */
const PhaseStream = ({ messages }) => {
    return (
        <div className="flex-1 overflow-y-auto p-8 space-y-12 relative">
            {/* Idle-State Cognitive Anchor */}
            {messages.length === 0 && (
                <div className="absolute inset-0 flex items-center justify-center p-8 pointer-events-none">
                    <div className="max-w-2xl text-center space-y-4 opacity-20 transition-opacity duration-1000 animate-fade-in">
                        <h1 className="text-3xl md:text-4xl font-serif font-normal text-neutral-100 leading-tight">
                            Nutri analyzes dishes as physical systems — heat, structure, chemistry, and perception.
                        </h1>
                        <p className="text-sm font-mono uppercase tracking-[0.2em] text-neutral-400">
                            Describe a dish, constraint, or sensory goal.
                        </p>
                    </div>
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

                    {/* Assistant Response - Phase Container */}
                    {msg.role === 'assistant' && (
                        <div className="flex flex-col gap-4">
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
                                <div className="flex items-center gap-3 ml-2 py-2 px-4 bg-accent/5 border-l-2 border-accent/40 rounded-r">
                                    <Binary className="w-4 h-4 text-accent animate-pulse-subtle" />
                                    <span className="text-sm font-mono text-accent/90 animate-fade-in">
                                        {msg.statusMessage}
                                    </span>
                                </div>
                            )}

                            {/* Legacy Fallback (if no statusMessage yet) */}
                            {msg.isStreaming && !msg.content && !msg.statusMessage && (
                                <div className="flex items-center gap-2 ml-2">
                                    <Binary className="w-4 h-4 text-accent animate-pulse-subtle" />
                                    <span className="text-[10px] font-mono uppercase tracking-widest text-neutral-500">
                                        Computational sequence in progress...
                                    </span>
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

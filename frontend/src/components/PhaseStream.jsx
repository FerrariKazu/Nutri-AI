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
        <div className="flex-1 overflow-y-auto p-8 space-y-12">
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

                            {msg.isStreaming && !msg.content && (
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

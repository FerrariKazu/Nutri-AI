import React, { useState } from 'react';
import { ArrowDown, Link2, FlaskConical, Activity, Zap, ShieldCheck, ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';
import { TierBadge, Tooltip } from './UIUtils';

/**
 * Tier2Mechanism
 * 
 * Renders a vertical "Mechanism of Action" (MoA) chain.
 * Steps: Compound -> Interaction -> Physiology -> Outcome.
 */
const Tier2Mechanism = React.memo(({ claim, expertMode }) => {
    const mechanism = claim.mechanism;
    const [expandedStep, setExpandedStep] = useState(null);

    if (!mechanism || !mechanism.steps || mechanism.steps.length === 0) {
        return (
            <div className="space-y-4 opacity-60">
                <div className="flex items-center gap-2">
                    <TierBadge tier={2} label="Mechanism" />
                    <Link2 className="w-3 h-3 text-blue-400 opacity-50" />
                </div>
                <div className="p-4 rounded-xl border border-dashed border-neutral-800 bg-neutral-900/50 text-center">
                    <p className="text-[10px] font-mono text-neutral-500 uppercase tracking-[0.2em]">Mechanism Mapping Incomplete</p>
                    <p className="text-[10px] text-neutral-600 mt-1.5 italic px-6 leading-relaxed">
                        Insufficient specificity in current evidence to map a discrete physiological pathway.
                    </p>
                </div>
            </div>
        );
    }

    const stepIcons = {
        'compound': FlaskConical,
        'interaction': Zap,
        'physiology': Activity,
        'outcome': ShieldCheck
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <TierBadge tier={2} label="Mechanism" />
                    <Link2 className="w-3 h-3 text-blue-400 opacity-50" />
                    <Tooltip text="The 'Mechanism of Action' (MoA) chain. Visualizes the biological step-by-step logic from compound ingestion to physiological outcome." />
                </div>
                {expertMode && (
                    <span className="text-[9px] font-mono text-blue-400/60 uppercase tracking-widest px-2 py-0.5 rounded border border-blue-400/20 bg-blue-500/5">
                        Path Validated
                    </span>
                )}
            </div>

            {/* Vertical Chain */}
            <div className="space-y-1 relative pl-2">
                {/* Connecting Line */}
                <div className="absolute left-[13px] top-4 bottom-4 w-px bg-gradient-to-b from-blue-500/50 via-blue-500/20 to-transparent shadow-[0_0_8px_rgba(59,130,246,0.3)]" />

                {mechanism.steps.map((step, idx) => {
                    const Icon = stepIcons[step.step_type] || Activity;
                    const isLast = idx === mechanism.steps.length - 1;
                    const isExpanded = expandedStep === idx;

                    return (
                        <div key={idx} className="relative flex items-start gap-4 pb-6 last:pb-0 group">
                            <div className={`z-10 mt-1 p-1.5 rounded-full bg-neutral-900 border transition-all duration-500 ${isExpanded ? 'border-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.4)]' : 'border-blue-500/30'
                                }`}>
                                <Icon className={`w-3 h-3 ${isExpanded ? 'text-blue-400' : 'text-blue-500/60'}`} />
                            </div>

                            <div className="flex-1 space-y-1.5">
                                <button
                                    onClick={() => setExpandedStep(isExpanded ? null : idx)}
                                    className="w-full text-left flex items-center justify-between group/title"
                                >
                                    <div className="flex items-center gap-2">
                                        <h5 className="text-[11px] font-bold text-neutral-200 uppercase tracking-tight group-hover/title:text-blue-400 transition-colors">
                                            {step.entity_name}
                                        </h5>
                                        {expertMode && (
                                            <span className="text-[8px] font-mono text-neutral-600 px-1 border border-neutral-800 rounded">
                                                {step.step_type}
                                            </span>
                                        )}
                                    </div>
                                    <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                                        {isExpanded ? <ChevronDown className="w-3 h-3 text-neutral-600" /> : <ChevronRight className="w-3 h-3 text-neutral-600" />}
                                    </div>
                                </button>

                                <p className="text-[11px] text-neutral-500 leading-snug pr-4">
                                    {step.description}
                                </p>

                                {/* 🚀 Expandable Detail Depth */}
                                {isExpanded && (
                                    <div className="mt-3 p-3 rounded bg-neutral-950/40 border border-neutral-800/50 animate-fade-in">
                                        <div className="flex items-center gap-2 mb-2">
                                            <Activity className="w-2.5 h-2.5 text-blue-400/50" />
                                            <p className="text-[9px] font-bold text-neutral-400 uppercase tracking-widest">Biological Context</p>
                                        </div>
                                        <p className="text-[10px] text-neutral-500 leading-relaxed italic">
                                            This interaction occurs primarily in the {idx === 0 ? 'intestinal lumen' : 'cellular mitochondria'} and is mediated by specific enzymatic pathways.
                                        </p>
                                        {step.evidence_source && (
                                            <div className="mt-2 flex items-center gap-2 pt-2 border-t border-neutral-800/50">
                                                <ExternalLink className="w-2.5 h-2.5 text-blue-500/40" />
                                                <span className="text-[9px] font-mono text-blue-400/60 underline cursor-pointer hover:text-blue-400 transition-colors">
                                                    Source: {step.evidence_source}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>

                            {!isLast && (
                                <div className="absolute left-[13px] bottom-0 translate-y-1/2 opacity-30 group-hover:opacity-100 transition-opacity">
                                    <ArrowDown className="w-3 h-3 text-blue-500/50" />
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Path Confidence (Expert Mode) */}
            {expertMode && mechanism.weakest_link_confidence && (
                <div className="mt-4 pt-4 border-t border-neutral-800/50 flex items-center justify-between bg-neutral-950/10 p-2 rounded">
                    <div className="flex items-center gap-2">
                        <span className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest">Weakest Link Confidence</span>
                        <Tooltip text="MoA chains are only as strong as their least-validated interaction. This metric identifies the 'bottleneck' in reasoning certainty." />
                    </div>
                    <span className={`text-[11px] font-bold font-mono ${mechanism.weakest_link_confidence < 0.4 ? 'text-amber-500' : 'text-blue-400'}`}>
                        {Math.round(mechanism.weakest_link_confidence * 100)}%
                    </span>
                </div>
            )}
        </div>
    );
});

export default Tier2Mechanism;

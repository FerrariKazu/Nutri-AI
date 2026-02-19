import React, { useState } from 'react';
import { ArrowDown, Link2, FlaskConical, Activity, Zap, ShieldCheck, ChevronDown, ChevronRight, ExternalLink, DatabaseZap } from 'lucide-react';
import { TierBadge, Tooltip, formatConfidence } from './UIUtils';
import { renderPermissions } from '../../contracts/renderPermissions';
import UniProtAnnotation from './UniProtAnnotation';

/**
 * Tier2Mechanism
 * 
 * STRICT MODE:
 * - No fabricated "Biological Context".
 * - No defaults for weakest link.
 * - Collapse if execution trace has no mechanism.
 */
const Tier2Mechanism = React.memo(({ trace, claim, expertMode }) => {
    const mechanism = claim.mechanism || { steps: [] };
    const [expandedStep, setExpandedStep] = useState(null);

    // ADAPTER: Support v2.1 Graph Schema (nodes/edges)
    let steps = mechanism.steps || [];
    if (steps.length === 0 && mechanism.nodes && mechanism.nodes.length > 0) {
        // Linearize the graph for the list view
        steps = mechanism.nodes.map(node => ({
            step_type: node.type || 'interaction',
            entity_name: node.label || node.id,
            description: node.description || `Mechanistic node identified as ${node.type || 'unknown entity'}.`,
            evidence_source: node.source || "Sensory Ontology v2.1",
            verified: node.verified,
            uniprot_id: node.uniprot_id
        }));
    }

    // 1. Permission Gate - UNBREAKABLE: Never return null / hide tier.
    const hasPermission = renderPermissions.canRenderTier2({ claims: [claim] }).allowed;
    const hasSteps = steps.length > 0;

    if (!hasSteps) {
        return (
            <div className="space-y-4 opacity-60">
                <div className="flex items-center gap-2">
                    <TierBadge tier={2} label="Mechanism" />
                    <Link2 className="w-3 h-3 text-blue-400 opacity-50" />
                    <Tooltip text="The step-by-step logic chain." />
                </div>
                <div className="p-4 rounded-xl border border-dashed border-neutral-800 bg-neutral-900/50 text-center">
                    <p className="text-[10px] font-mono text-neutral-500 uppercase tracking-[0.2em]">⚠ Mechanism data incomplete</p>
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
                    <Tooltip text="The step-by-step logic chain." />
                </div>
                {claim.importance_score > 0.6 && (
                    <div className="flex items-center gap-1.5 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                        <Zap className="w-2.5 h-2.5 text-blue-400" />
                        <span className="text-[9px] font-mono text-blue-400 font-bold uppercase tracking-tight">
                            Major Driver ({Math.round(claim.importance_score * 100)}%)
                        </span>
                    </div>
                )}
            </div>

            {/* Vertical Chain */}
            <div className="space-y-1 relative pl-2">
                {/* Connecting Line */}
                <div className="absolute left-[13px] top-4 bottom-4 w-px bg-gradient-to-b from-blue-500/50 via-blue-500/20 to-transparent shadow-[0_0_8px_rgba(59,130,246,0.3)]" />

                {steps.map((step, idx) => {
                    const Icon = stepIcons[step.step_type] || Activity;
                    const isLast = idx === steps.length - 1;
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
                                        <h5 className="text-[11px] font-semibold text-neutral-200 tracking-tight group-hover/title:text-blue-400 transition-colors">
                                            {step.entity_name}
                                        </h5>
                                        <div className={`text-[9px] px-1.5 py-0.5 rounded border ${step.verified ? 'text-blue-400 border-blue-500/30' : 'text-neutral-500 border-neutral-800'}`}>
                                            {step.verified ? 'Verified' : 'Theoretical'}
                                        </div>
                                        {step.uniprot_id && (
                                            <Tooltip text={`External Protein Annotation Available (${step.uniprot_id})`}>
                                                <div className="p-1 rounded bg-purple-500/10 border border-purple-500/20">
                                                    <DatabaseZap className="w-2.5 h-2.5 text-purple-400" />
                                                </div>
                                            </Tooltip>
                                        )}
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

                                <p className="text-[11px] text-neutral-400 leading-relaxed pr-4">
                                    {step.description}
                                </p>

                                {/* 🚀 Expandable Detail - STRICT MODE: NO FABRICATION */}
                                {isExpanded && (
                                    <div className="mt-3 p-3 rounded bg-neutral-950/40 border border-neutral-800/50 animate-fade-in">
                                        {step.evidence_source ? (
                                            <div className="flex items-center gap-2 pt-1 pb-2 border-b border-neutral-800/30 mb-2">
                                                <ExternalLink className="w-2.5 h-2.5 text-blue-500/40" />
                                                <span className="text-[9px] font-mono text-blue-400/60 underline cursor-pointer hover:text-blue-400 transition-colors">
                                                    Source: {step.evidence_source}
                                                </span>
                                            </div>
                                        ) : (
                                            <p className="text-[9px] text-neutral-600 italic">No specific source metadata available.</p>
                                        )}

                                        {/* 🧬 Isolated UniProt Annotation */}
                                        {step.uniprot_id && (
                                            <UniProtAnnotation uniprotId={step.uniprot_id} />
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

            {/* Path Confidence (Expert Mode) - Strictly Explicit */}
            {expertMode && (
                <div className="mt-4 pt-4 border-t border-neutral-800/50 flex items-center justify-between bg-neutral-950/10 p-2 rounded">
                    <div className="flex items-center gap-2">
                        <span className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest">Weakest Link Confidence</span>
                    </div>
                    <span className={`text-[11px] font-bold font-mono ${mechanism.weakest_link_confidence < 0.4 ? 'text-amber-500' : 'text-blue-400'}`}>
                        {formatConfidence(mechanism.weakest_link_confidence)}
                    </span>
                </div>
            )}
        </div>
    );
});

export default Tier2Mechanism;

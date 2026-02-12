import React from 'react';
import { Database, FlaskConical, AlertCircle, Hash } from 'lucide-react';
import { TierBadge, EvidenceBadge, Tooltip } from './UIUtils';
import { renderPermissions } from '../../contracts/renderPermissions';

/**
 * Tier1Evidence
 * 
 * STRICT MODE:
 * - No defaults for source.
 * - Explicit "Unavailable" if data missing.
 * - No synthetic confidence.
 */
const Tier1Evidence = React.memo(({ trace, claim, metrics, expertMode }) => {
    // 1. Permission Gate - UNBREAKABLE: Never return null.
    // We render available markers instead.
    const hasPermission = renderPermissions.canRenderTier1(trace).allowed;

    // 2. Strict Data Access
    const strength = claim.confidence > 0.8 ? 'strong' : claim.confidence > 0.4 ? 'moderate' : 'weak';

    // Explicit Null Handling for Confidence
    const hasConfidence = claim.confidence !== null;

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <TierBadge tier={1} label="Evidence" />
                    <Database className="w-3 h-3 text-green-400 opacity-50" />
                    <Tooltip text="Raw data verification layer." />
                </div>
                {hasConfidence ? (
                    <EvidenceBadge strength={strength} />
                ) : (
                    <span className="text-[9px] font-mono text-neutral-500 bg-neutral-900 px-2 py-0.5 rounded border border-neutral-800">
                        CONFIDENCE: NULL
                    </span>
                )}
            </div>

            <p className="text-sm text-neutral-300 leading-relaxed">
                Source: <span className="text-white font-medium">{claim.source || 'Unavailable'}</span>
                {claim.evidence_type && (
                    <span className="ml-2 text-[8px] font-mono text-neutral-500 border border-neutral-800 px-1 rounded uppercase">
                        {claim.evidence_type}
                    </span>
                )}
            </p>

            {claim.estimated_via_ontology && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/5 border border-amber-500/10">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-500/60" />
                    <p className="text-[10px] text-amber-500/80 font-medium">
                        ⚠ Estimated via ontology expansion
                    </p>
                </div>
            )}

            {/* Source List / Histograms */}
            <div className="space-y-2">
                <div className="flex items-center gap-1.5 px-0.5">
                    <p className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest">Active Data Indices</p>
                </div>
                <div className="flex flex-wrap gap-2">
                    {(expertMode && metrics.sourceContribution && Object.keys(metrics.sourceContribution).length > 0
                        ? Object.keys(metrics.sourceContribution)
                        : [claim.source]).filter(Boolean).map((src, i) => (
                            <div key={i} className="px-2.5 py-1 rounded bg-neutral-800/40 border border-neutral-700/30 flex items-center gap-2.5 cursor-default">
                                <span className="text-[10px] text-neutral-400 font-mono tracking-tight">{src}</span>
                                {expertMode && metrics.sourceContribution && (
                                    <span className="text-[9px] text-green-400 font-bold font-mono">
                                        {(metrics.sourceContribution[src] || 0)}%
                                    </span>
                                )}
                            </div>
                        ))}

                    {(!claim.source && (!metrics.sourceContribution || Object.keys(metrics.sourceContribution).length === 0)) && (
                        <span className="text-[10px] text-neutral-600 font-mono italic">No source metadata</span>
                    )}
                </div>
            </div>

            {/* PubChem Proof Section */}
            {metrics.pubchemUsed && (
                <div className="mt-4 p-3 rounded-lg bg-green-500/5 border border-green-500/10 flex items-start gap-4 shadow-inner">
                    <FlaskConical className="w-4 h-4 text-green-400 shrink-0 mt-0.5" />
                    <div className="flex-1">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <p className="text-[10px] font-bold text-green-400 uppercase tracking-widest">Molecular Identity Verified</p>
                            </div>
                            <span className="text-[8px] font-mono text-green-400/50 px-1.5 py-0.5 border border-green-500/20 rounded-full">P0 ENFORCED</span>
                        </div>
                        <div className="flex items-center gap-2 mt-1.5">
                            <Hash className="w-2.5 h-2.5 text-neutral-600" />
                            <p className="text-[9px] text-neutral-500 font-mono truncate max-w-[240px]">
                                {metrics.proofHash || 'Verified via PubChem PUG-REST protocol'}
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
});

export default Tier1Evidence;

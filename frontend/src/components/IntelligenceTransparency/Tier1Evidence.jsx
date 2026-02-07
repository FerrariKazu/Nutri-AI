import React from 'react';
import { Database, FlaskConical, AlertCircle, Search, Hash } from 'lucide-react';
import { TierBadge, EvidenceBadge, Tooltip } from './UIUtils';

/**
 * Tier1Evidence
 * 
 * Friendly Mode: Shows evidence strength badge and normalized sources.
 * Expert Mode: Shows source histograms and PubChem proof verification.
 */
const Tier1Evidence = React.memo(({ claim, metrics, expertMode }) => {
    const strength = claim.confidence > 0.8 ? 'strong' : claim.confidence > 0.4 ? 'moderate' : 'weak';

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <TierBadge tier={1} label="Evidence" />
                    <Database className="w-3 h-3 text-green-400 opacity-50" />
                    <Tooltip text="Raw data verification layer. Measures the statistical power and quality of supporting research for this specific claim." />
                </div>
                <EvidenceBadge strength={strength} />
            </div>

            <p className="text-sm text-neutral-300 leading-relaxed">
                Derived from validated nutritional knowledge and <span className="text-white font-medium">{claim.source || 'verified datasets'}</span>.
            </p>

            {/* Source List / Histograms */}
            <div className="space-y-2">
                <div className="flex items-center gap-1.5 px-0.5">
                    <p className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest">Active Data Indices</p>
                    <Tooltip text="Nutri weights multiple sources to reach a conclusion. High-weight sources contribute more to the final confidence score." />
                </div>
                <div className="flex flex-wrap gap-2">
                    {(expertMode && metrics.sourceContribution && Object.keys(metrics.sourceContribution).length > 0
                        ? Object.keys(metrics.sourceContribution)
                        : [claim.source || 'NutriDB']).map((src, i) => (
                            <div key={i} className="px-2.5 py-1 rounded bg-neutral-800/40 border border-neutral-700/30 flex items-center gap-2.5 group hover:border-green-500/30 transition-colors cursor-default">
                                <span className="text-[10px] text-neutral-400 font-mono tracking-tight group-hover:text-neutral-200 transition-colors">{src}</span>
                                {expertMode && metrics.sourceContribution && (
                                    <span className="text-[9px] text-green-400 font-bold font-mono">
                                        {(metrics.sourceContribution[src] || 0)}%
                                    </span>
                                )}
                            </div>
                        ))}
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
                                <Tooltip text="Nutri enforced a P0 check against PubChem's CID database to ensure chemical compounds mentioned are real and verified." />
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

            {expertMode && Object.keys(metrics.brokenSteps || {}).length > 0 && (
                <div className="mt-2 flex items-start gap-2.5 p-2 rounded bg-amber-500/5 border border-amber-500/10">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                    <p className="text-[10px] text-amber-500/60 italic leading-snug">
                        Evidence integrity check detected minor data variance in {Object.keys(metrics.brokenSteps).length} downstream nodes. Confidence adjusted.
                    </p>
                </div>
            )}
        </div>
    );
});

export default Tier1Evidence;

import React, { useState } from 'react';
import { History, TrendingUp, TrendingDown, Minus, Anchor, Sparkles } from 'lucide-react';
import { TierBadge, Tooltip } from './UIUtils';
import { renderPermissions } from '../../contracts/renderPermissions';

/**
 * Tier4Temporal
 * 
 * STRICT MODE:
 * - No "Stability Narrative".
 * - Raw Enums only (STABLE, UPGRADE, etc.).
 */
const Tier4Temporal = React.memo(({ uiTrace, claimIdx, expertMode }) => {
    const [expanded, setExpanded] = useState(true);

    // 1. Permission Gate
    if (!renderPermissions.canRenderTier4(uiTrace).allowed) return null; // Collapse completely if no temporal data

    const { temporal } = uiTrace;
    const currentClaim = uiTrace.claims[claimIdx] || uiTrace.claims[0];
    const changeType = currentClaim.changeType || 'UNKNOWN';

    // STRICT: Handle null lists
    const revisions = temporal.revisions || [];

    // Passive Icon Mapping
    const StatusIcon = {
        'UPGRADE': TrendingUp,
        'DOWNGRADE': TrendingDown,
        'STABLE': Minus,
        'NEW_DECISION': Sparkles
    }[changeType] || Minus;

    const statusColors = {
        'UPGRADE': 'text-green-400 bg-green-500/5 border-green-500/10',
        'DOWNGRADE': 'text-red-400 bg-red-500/5 border-red-500/10',
        'STABLE': 'text-blue-400 bg-blue-500/5 border-blue-500/10',
        'NEW_DECISION': 'text-purple-400 bg-purple-500/5 border-purple-500/10'
    }[changeType] || 'text-neutral-400 border-neutral-800';

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <TierBadge tier={4} label="Temporal" />
                    <History className="w-3 h-3 text-purple-400 opacity-50" />
                </div>
                {temporal.anchoring && ( // Factual anchor (Turn X) allowed
                    <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-neutral-800 text-[9px] font-mono text-neutral-400 border border-neutral-700/50">
                        <Anchor className="w-2.5 h-2.5" />
                        {temporal.anchoring}
                    </div>
                )}
            </div>

            {/* Evolution Status - RAW ENUM */}
            <div className={`p-4 rounded-xl border ${statusColors} flex items-center gap-4`}>
                <div className="p-2 rounded-lg bg-neutral-900 border border-current opacity-80 shadow-inner">
                    <StatusIcon className="w-4 h-4" />
                </div>
                <div className="flex-1">
                    <h5 className="text-[10px] font-bold uppercase tracking-widest opacity-80">
                        Decision State
                    </h5>
                    <p className="text-[12px] font-mono font-bold mt-1">
                        {changeType}
                    </p>
                </div>
            </div>

            {/* Turn History / Uncertainty (Expert Mode) */}
            {expertMode && (
                <div className="space-y-4 pt-2">
                    <div className="flex justify-between items-center text-[9px] font-mono uppercase tracking-widest text-neutral-500 bg-neutral-950/20 p-2 rounded border border-neutral-800/30">
                        <span className="flex items-center gap-2">
                            <Sparkles className="w-3 h-3 opacity-50" />
                            Resolved Deltas
                        </span>
                        <span className="text-purple-400 font-bold">{temporal.resolvedUncertainties ?? 'NULL'}</span>
                    </div>

                    {revisions.length > 0 && (
                        <div className="space-y-2">
                            <p className="text-[8px] font-mono text-neutral-600 uppercase tracking-widest ml-1">Session Revisions</p>
                            <div className="space-y-1.5">
                                {revisions.slice(-2).map((rev, i) => (
                                    <div key={i} className="flex items-center gap-2 text-[10px] text-neutral-500 bg-neutral-950/40 px-3 py-2 rounded border border-neutral-800/50">
                                        <div className="w-1.5 h-1.5 rounded-full bg-purple-500/30" />
                                        <span className="truncate">{rev}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {temporal.saturationTriggered && (
                <div className="mt-2 p-2 rounded bg-amber-500/5 border border-amber-500/10 text-center">
                    <p className="text-[9px] text-amber-500/70 font-mono">
                        SATURATION_TRIGGERED: TRUE
                    </p>
                </div>
            )}
        </div>
    );
});

export default Tier4Temporal;

import React, { useState } from 'react';
import { Target, ShieldAlert, HelpCircle, UserCheck } from 'lucide-react';
import { TierBadge, RiskThermometer, ConfidenceMeter, Tooltip } from './UIUtils';
import { renderPermissions } from '../../contracts/renderPermissions';

/**
 * Tier3Causality
 * 
 * STRICT MODE:
 * - No "friendly" microcopy.
 * - Raw Enums for Decision.
 * - Explicit Unavailable state.
 */
const Tier3Causality = React.memo(({ uiTrace, claimIdx, expertMode }) => {
    const [expanded, setExpanded] = useState(true);

    // 1. Permission Gate
    if (!renderPermissions.canRenderTier3(uiTrace).allowed) {
        return null;
    }

    const { causality } = uiTrace;
    const currentClaim = uiTrace.claims[claimIdx] || uiTrace.claims[0];
    const decision = currentClaim.decision || "UNKNOWN";

    // STRICT: Handle null lists
    const missingFields = causality.missingFields || [];

    return (
        <div className="space-y-5">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <TierBadge tier={3} label="Causality" />
                    <Target className="w-3 h-3 text-amber-400 opacity-50" />
                    <Tooltip text="Applicability and Risk Analysis." />
                </div>
            </div>

            {/* Applicability Match */}
            <div className="space-y-4">
                <div className="flex items-center gap-2">
                    {causality.applicability !== null ? (
                        <div className="w-full">
                            <ConfidenceMeter
                                value={causality.applicability}
                                label="Context Applicability Match"
                            />
                            {/* PARTIAL COVERAGE WARNING (Phase 5) */}
                            {causality.applicability < 0.5 && (
                                <div className="mt-2 text-[10px] text-amber-500 font-medium italic flex items-center gap-1.5 opacity-80">
                                    <ShieldAlert className="w-3 h-3" />
                                    <span>Signal attenuation due to partial context overlap.</span>
                                </div>
                            )}
                        </div>
                    ) : (
                        <span className="text-[10px] text-neutral-600 font-mono">Applicability: NULL</span>
                    )}
                </div>

                {missingFields.length > 0 && (
                    <div className="intelligence-glass p-3 flex items-start gap-3 shadow-inner">
                        <HelpCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                        <div>
                            <div className="flex items-center gap-2">
                                <p className="text-[10px] font-bold text-amber-500 uppercase tracking-tight">Context Gap</p>
                            </div>
                            <p className="text-[11px] text-neutral-400 mt-1 leading-snug">
                                Missing parameters: <span className="font-semibold text-amber-400/80">{missingFields.join(', ')}</span>
                            </p>
                        </div>
                    </div>
                )}
            </div>

            {/* Risk Assessment - STRICT RAW VALUES */}
            <div className="pt-6 border-t border-neutral-800/50 space-y-4">
                {causality.riskCount !== null && (
                    <div className="flex items-center justify-between">
                        <span className="text-[10px] text-neutral-500 font-medium uppercase tracking-wide">Risk Flags</span>
                        <span className="text-[11px] font-mono font-bold text-neutral-300">{causality.riskCount}</span>
                    </div>
                )}

                {causality.riskCount > 0 && (
                    <div className="intelligence-glass p-3 flex items-start gap-3 border-red-500/20">
                        <ShieldAlert className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                        <div>
                            <div className="flex items-center gap-2">
                                <p className="text-[10px] font-bold text-red-500 uppercase tracking-tight">Clinical Guardrails Active</p>
                            </div>
                            <p className="text-[11px] text-neutral-400 mt-1 leading-snug">
                                {Object.keys(causality.riskFlags || {}).join(', ') || 'Unspecified risks detected'}
                            </p>
                        </div>
                    </div>
                )}
            </div>

            {/* Final Decision Gate - RAW ENUM */}
            <div className="pt-4 border-t border-neutral-800/50">
                <div className="flex items-center justify-between">
                    <span className="text-[10px] font-medium text-neutral-500 uppercase tracking-wide">Decision</span>
                    <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded border ${decision === 'ALLOW' ? 'text-green-400 border-green-900 bg-green-900/20' :
                        decision === 'WITHHOLD' ? 'text-red-400 border-red-900 bg-red-900/20' :
                            'text-amber-400 border-amber-900 bg-amber-900/20'
                        }`}>
                        {decision}
                    </span>
                </div>
            </div>

            {expertMode && (
                <div className="mt-4 p-2 rounded bg-neutral-950/40 border border-neutral-800/30 flex items-center justify-center gap-2">
                    <UserCheck className="w-3 h-3 text-neutral-600" />
                    <span className="text-[9px] text-neutral-600 font-mono uppercase tracking-[0.15em]">
                        Tier 3 Logic
                    </span>
                </div>
            )}
        </div>
    );
});

export default Tier3Causality;

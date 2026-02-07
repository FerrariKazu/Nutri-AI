import React from 'react';
import { Target, ShieldAlert, AlertCircle, HelpCircle, UserCheck } from 'lucide-react';
import { TierBadge, RiskThermometer, ConfidenceMeter, ResponsibleDecision, Tooltip } from './UIUtils';

/**
 * Tier3Causality
 * 
 * Integrates:
 * - Applicability (Match quality meter)
 * - Risk Engine (Severity thermometer)
 * - Responsible Decision (Microcopy-mapped recommendations)
 */
const Tier3Causality = React.memo(({ uiTrace, claimIdx, expertMode }) => {
    const { causality } = uiTrace;
    const currentClaim = uiTrace.claims[claimIdx] || uiTrace.claims[0];

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <TierBadge tier={3} label="Causality" />
                    <Target className="w-3 h-3 text-amber-400 opacity-50" />
                    <Tooltip text="Analyzes how well Nutri's general knowledge matches your specific biological profile and clinical context." />
                </div>
            </div>

            {/* Applicability Match */}
            <div className="space-y-4">
                <div className="flex items-center gap-2">
                    <ConfidenceMeter
                        value={causality.applicability}
                        label="Context Applicability Match"
                    />
                </div>

                {causality.missingFields.length > 0 && (
                    <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/10 flex items-start gap-3 shadow-inner">
                        <HelpCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                        <div>
                            <div className="flex items-center gap-2">
                                <p className="text-[10px] font-bold text-amber-500 uppercase tracking-tight">Information Gap Detected</p>
                                <Tooltip text="Nutri identified missing parameters in your profile that would increase reasoning precision." />
                            </div>
                            <p className="text-[11px] text-neutral-400 mt-1 leading-snug">
                                Nutri needs a little more information about your <span className="font-bold text-amber-400/80">{causality.missingFields.join(', ')}</span> for a specialized assessment.
                            </p>
                        </div>
                    </div>
                )}
            </div>

            {/* Risk Assessment */}
            <div className="pt-6 border-t border-neutral-800/50 space-y-4">
                <RiskThermometer severity={causality.riskCount > 0 ? 0.8 : 0.1} />

                {causality.riskCount > 0 && (
                    <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/10 flex items-start gap-3 animate-pulse-slow">
                        <ShieldAlert className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                        <div>
                            <div className="flex items-center gap-2">
                                <p className="text-[10px] font-bold text-red-500 uppercase tracking-tight text-glow-red">Active Safety Guardrails</p>
                                <Tooltip text="Clinical safety filters triggered based on your medical profile (e.g., allergies, conditions, or medications)." />
                            </div>
                            <p className="text-[11px] text-neutral-400 mt-1 leading-snug">
                                Potential clinical risks or contraindications detected. Nutri has adjusted recommendations to prioritize your safety.
                            </p>
                        </div>
                    </div>
                )}
            </div>

            {/* Final Decision Gate */}
            <div className="pt-4 border-t border-neutral-800/50">
                <ResponsibleDecision meta={currentClaim.decisionMeta} />
            </div>

            {expertMode && (
                <div className="mt-4 p-2 rounded bg-neutral-950/40 border border-neutral-800/30 flex items-center justify-center gap-2">
                    <UserCheck className="w-3 h-3 text-neutral-600" />
                    <span className="text-[9px] text-neutral-600 font-mono uppercase tracking-[0.15em]">
                        Logic: Contextual Causality Engine (Tier 3)
                    </span>
                </div>
            )}
        </div>
    );
});

export default Tier3Causality;

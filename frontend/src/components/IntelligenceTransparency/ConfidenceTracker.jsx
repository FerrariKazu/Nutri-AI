import React from 'react';
import { TrendingDown, Target, Scale, Plus } from 'lucide-react';
import { Tooltip, getConfidenceNarrative } from './UIUtils';

/**
 * ConfidenceTracker
 * 
 * Visualizes confidence deltas and movement.
 * Displays "Previous -> Current" with movement indicators and narrative.
 */
const ConfidenceTracker = React.memo(({ uiTrace, expertMode }) => {
    const metrics = uiTrace?.metrics || {};
    const breakdown = metrics.confidence_breakdown || {
        baseline: 0,
        multipliers: [],
        policy_adjustment: 0,
        final: 0
    };

    const finalPercentage = Math.round(breakdown.final * 100);
    const baselinePercentage = Math.round(breakdown.baseline * 100);

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Target className="w-3 h-3 text-neutral-400 opacity-50" />
                    <span className="text-[10px] font-mono text-neutral-500 uppercase tracking-widest">Confidence Discipline</span>
                    <Tooltip text="Direct arithmetic trace of belief generation. Never re-computed in the UI." />
                </div>
                <div className="flex items-center gap-2 px-2 py-0.5 rounded border border-blue-500/20 bg-blue-500/5">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
                    <span className="text-[9px] font-bold text-blue-400 uppercase tracking-widest font-mono">
                        Server Asserted
                    </span>
                </div>
            </div>

            {/* 📏 Arithmetic Path */}
            <div className="space-y-4">
                {/* 1. Baseline */}
                <div className="flex items-center justify-between group">
                    <div className="flex items-center gap-2">
                        <span className="text-[10px] text-neutral-600 font-mono">01</span>
                        <span className="text-[10px] text-neutral-400 uppercase font-bold tracking-tight">Baseline Evidence</span>
                    </div>
                    <span className="text-[10px] text-neutral-200 font-mono">{baselinePercentage}%</span>
                </div>

                {/* 2. Multipliers / Penalties */}
                {breakdown.multipliers && breakdown.multipliers.length > 0 ? (
                    breakdown.multipliers.map((m, idx) => (
                        <div key={idx} className="flex items-center justify-between pl-4 border-l border-neutral-800 ml-1">
                            <div className="flex items-center gap-2">
                                {m.value < 0 ? (
                                    <TrendingDown className="w-3 h-3 text-red-500/50" />
                                ) : (
                                    <Plus className="w-3 h-3 text-green-500/50" />
                                )}
                                <span className="text-[10px] text-neutral-500 uppercase font-medium">{m.label}</span>
                            </div>
                            <span className={`text-[10px] font-mono ${m.value < 0 ? 'text-red-400/80' : 'text-green-400/80'}`}>
                                {m.value > 0 ? '+' : ''}{Math.round(m.value * 100)}%
                            </span>
                        </div>
                    ))
                ) : (
                    <div className="flex items-center justify-between pl-4 border-l border-neutral-800 ml-1">
                        <div className="flex items-center gap-2">
                            <Plus className="w-3 h-3 text-green-500/50" />
                            <span className="text-[10px] text-neutral-500 uppercase font-medium">Universal Verification</span>
                        </div>
                        <span className="text-[10px] text-green-400/80 font-mono">+0%</span>
                    </div>
                )}

                {/* 3. Policy Adjustment */}
                {Math.abs(breakdown.policy_adjustment) > 0 && (
                    <div className="flex items-center justify-between pl-4 border-l border-neutral-800 ml-1">
                        <div className="flex items-center gap-2">
                            <Scale className="w-3 h-3 text-amber-500/50" />
                            <span className="text-[10px] text-neutral-500 uppercase font-medium">Policy Normalization</span>
                        </div>
                        <span className={`text-[10px] font-mono ${breakdown.policy_adjustment < 0 ? 'text-red-400/80' : 'text-green-400/80'}`}>
                            {breakdown.policy_adjustment > 0 ? '+' : ''}{Math.round(breakdown.policy_adjustment * 100)}%
                        </span>
                    </div>
                )}

                {/* 4. Final Belief */}
                <div className="pt-4 border-t border-neutral-800 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-neutral-900 border border-neutral-800 rounded">
                            <Target className="w-4 h-4 text-white" />
                        </div>
                        <div className="flex flex-col">
                            <span className="text-[9px] text-neutral-500 font-bold uppercase tracking-widest">Final Belief</span>
                            <span className="text-xl font-bold text-white font-mono leading-none tracking-tight">
                                {finalPercentage}%
                            </span>
                        </div>
                    </div>
                    {expertMode && (
                        <div className="text-[9px] font-mono text-neutral-600 bg-neutral-900 px-2 py-1 rounded border border-neutral-800">
                            SSOT Asserted
                        </div>
                    )}
                </div>
            </div>

            {/* 🚀 Confidence Narrative (Verbatim from metrics) */}
            <div className="px-4 py-3 rounded bg-neutral-900/40 border border-neutral-800/50 italic">
                <p className="text-[11px] text-neutral-400 text-center leading-relaxed">
                    "{getConfidenceNarrative(breakdown.final)}"
                </p>
            </div>
        </div>
    );
});

export default ConfidenceTracker;

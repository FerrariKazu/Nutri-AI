import React from 'react';
import { Scale, Plus, Minus, Equal, ArrowRight } from 'lucide-react';

/**
 * RuleFiringTimeline
 * 
 * ARITHMETIC AUDIT TERMINAL:
 * - Shows cumulative math of confidence scoring.
 * - Format: Previous Score -> Rule [Delta] -> New Score.
 * - Prevents opaque "AI opinion" by exposing the math stack.
 */
const RuleFiringTimeline = ({ breakdown }) => {
    if (!breakdown || !breakdown.rule_firings) return null;

    let runningScore = breakdown.baseline_used || 0;

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2 px-1">
                <p className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest">Confidence Arithmetic (Trace)</p>
            </div>

            <div className="space-y-2 relative">
                {/* Baseline Entry */}
                <div className="flex items-center justify-between p-2 rounded bg-neutral-900 border border-neutral-800 border-dashed">
                    <span className="text-[10px] text-neutral-500 font-mono uppercase">Starting Baseline</span>
                    <span className="text-[10px] font-bold text-neutral-400 font-mono">{runningScore.toFixed(3)}</span>
                </div>

                <div className="space-y-1 pl-4 border-l border-neutral-800">
                    {breakdown.rule_firings.map((rf, idx) => {
                        const previous = runningScore;
                        const delta = rf.contribution || 0;
                        if (rf.fired) {
                            runningScore += delta;
                        }
                        const current = runningScore;

                        return (
                            <div key={idx} className={`p-2 rounded-lg border transition-colors ${rf.fired ? 'bg-neutral-900/40 border-neutral-700' : 'bg-transparent border-transparent opacity-30'
                                }`}>
                                <div className="flex items-start justify-between mb-1">
                                    <div className="flex items-center gap-2">
                                        <span className="text-[10px] font-black text-neutral-300 tracking-tight uppercase">{rf.rule_id}</span>
                                        <span className="text-[8px] font-mono text-neutral-600">[{rf.category}]</span>
                                    </div>
                                    <div className={`text-[10px] font-black font-mono ${delta > 0 ? 'text-green-500' : delta < 0 ? 'text-red-500' : 'text-neutral-500'}`}>
                                        {rf.fired ? (delta > 0 ? `+${delta.toFixed(3)}` : delta.toFixed(3)) : 'SKIP'}
                                    </div>
                                </div>

                                {rf.fired && (
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2 overflow-hidden">
                                            <span className="text-[8px] font-mono text-neutral-600 truncate">in: {JSON.stringify(rf.input)}</span>
                                        </div>
                                        <div className="flex items-center gap-1 text-[9px] font-mono text-neutral-500">
                                            <span>{previous.toFixed(3)}</span>
                                            <ArrowRight className="w-2 h-2" />
                                            <span className="text-white font-bold">{current.toFixed(3)}</span>
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* Final Total */}
                <div className="flex items-center justify-between p-3 rounded-lg bg-blue-500/5 border border-blue-500/20 mt-4 shadow-inner">
                    <div className="flex items-center gap-2">
                        <Equal className="w-4 h-4 text-blue-400" />
                        <span className="text-[11px] font-black text-blue-400 uppercase tracking-widest">Final Audit Score</span>
                    </div>
                    <span className="text-sm font-black text-white font-mono">{runningScore.toFixed(3)}</span>
                </div>
            </div>

            <p className="text-[8px] font-mono text-neutral-600 px-1 italic">
                * Cumulative precision monitored at 3 decimal places.
            </p>
        </div>
    );
};

export default RuleFiringTimeline;

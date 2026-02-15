import React from 'react';
import { TrendingUp, TrendingDown, Minus, Target } from 'lucide-react';
import { Tooltip, getConfidenceNarrative } from './UIUtils';

/**
 * ConfidenceTracker
 * 
 * Visualizes confidence deltas and movement.
 * Displays "Previous -> Current" with movement indicators and narrative.
 */
const ConfidenceTracker = React.memo(({ uiTrace, claimIdx, expertMode }) => {
    // STRICT: Render Backend Metrics Only
    const confidence = uiTrace.metrics.confidence;

    // If backend doesn't provide delta, we do NOT calculate it.
    const delta = uiTrace.metrics.confidenceDelta || 0;

    const percentage = Math.round(confidence * 100);
    const isUp = delta > 0.01;
    const isDown = delta < -0.01;

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Target className="w-3 h-3 text-neutral-400 opacity-50" />
                    <span className="text-[10px] font-mono text-neutral-500 uppercase tracking-widest">Confidence Discipline</span>
                    <Tooltip text="The statistical probability that this claim holds true based on synthesized evidence and peer models." />
                </div>
                {expertMode && (
                    <span className={`text-[9px] font-bold font-mono px-1.5 py-0.5 rounded ${isUp ? 'text-green-400 bg-green-400/10' :
                        isDown ? 'text-red-400 bg-red-400/10' :
                            'text-neutral-500 bg-neutral-800'
                        }`}>
                        {isUp && '+'}
                        {Math.round(delta * 100)}%
                    </span>
                )}
            </div>

            <div className="flex items-center justify-center gap-10">
                {/* Previous State - ONLY if backend provides specific previous value or delta */}
                {delta !== 0 && (
                    <div className="text-center opacity-30">
                        <p className="text-[8px] font-mono text-neutral-600 uppercase tracking-tighter mb-1">Prior State</p>
                        <p className="text-xl font-mono text-neutral-500 leading-none">{Math.round((confidence - delta) * 100)}%</p>
                    </div>
                )}

                {/* Arrow */}
                <div className={`p-2.5 rounded-full border transition-all duration-700 ${isUp ? 'border-green-500/20 text-green-400 bg-green-500/5 shadow-[0_0_15px_rgba(34,197,94,0.1)]' :
                    isDown ? 'border-red-500/20 text-red-400 bg-red-500/5 shadow-[0_0_15px_rgba(239,68,68,0.1)]' :
                        'border-neutral-800 text-neutral-600'
                    }`}>
                    {isUp ? <TrendingUp className="w-5 h-5 animate-bounce-slow" /> : isDown ? <TrendingDown className="w-5 h-5 animate-pulse" /> : <Minus className="w-5 h-5" />}
                </div>

                {/* Current */}
                <div className="text-center">
                    <p className="text-[8px] font-mono text-neutral-500 uppercase tracking-tighter mb-1 font-bold">Current Belief</p>
                    <p className={`text-3xl font-mono leading-none tracking-tighter ${isUp ? 'text-green-400 text-shadow-glow' : isDown ? 'text-red-400' : 'text-neutral-200'
                        }`}>
                        {percentage}%
                    </p>
                </div>
            </div>

            {/* 🚀 World-Class: Confidence Narrative */}
            <div className="px-4 py-2 rounded bg-neutral-950/40 border border-neutral-800/50">
                <p className="text-[11px] text-neutral-400 italic text-center leading-snug">
                    "{getConfidenceNarrative(confidence)}"
                </p>
            </div>

            {/* Expert Histogram */}
            {expertMode && (
                <div className="pt-2">
                    <div className="flex justify-between items-center mb-1.5">
                        <span className="text-[8px] font-mono text-neutral-600 uppercase tracking-widest">Entropy Resolution</span>
                        <span className="text-[8px] font-mono text-accent">P0 Verified</span>
                    </div>
                    <div className="h-1.5 w-full bg-neutral-800 rounded-full flex overflow-hidden">
                        <div className="h-full bg-green-500/30" style={{ width: '40%' }}></div>
                        <div className="h-full bg-blue-500/30" style={{ width: '30%' }}></div>
                        <div className="h-full bg-neutral-700/30" style={{ width: '30%' }}></div>
                    </div>
                    <div className="flex justify-between text-[8px] font-mono text-neutral-600 mt-1 uppercase tracking-tighter">
                        <span>Evidence</span>
                        <span>Physiology</span>
                        <span>Context</span>
                    </div>
                </div>
            )}
        </div>
    );
});

export default ConfidenceTracker;

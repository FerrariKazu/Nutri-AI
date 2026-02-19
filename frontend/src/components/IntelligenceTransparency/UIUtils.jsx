import React, { useState } from 'react';
import { ShieldCheck, AlertTriangle, Info, CheckCircle2, Beaker, HelpCircle } from 'lucide-react';

/**
 * Shared UI components for the Intelligence Transparency UI.
 * Consistent with Nutri's "Clinical but Warm" aesthetic.
 */

export const formatConfidence = (value) => {
    if (value === null || value === undefined || isNaN(value)) return "—";
    return `${Math.round(value * 100)}%`;
};

export const formatMetric = (value, type = 'text') => {
    if (value === null || value === undefined || isNaN(value)) {
        if (type === 'percent') return "—";
        if (type === 'density') return "Theoretical-only";
        if (type === 'resolution') return "Partial";
        return "—";
    }
    if (type === 'percent') return `${Math.round(value * 100)}%`;
    if (type === 'decimal') return value.toFixed(3);
    return value;
};

export const TierBadge = ({ tier, label }) => {
    const colors = {
        1: 'bg-green-500/10 text-green-400 border-green-500/20',
        2: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
        3: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
        4: 'bg-purple-500/10 text-purple-400 border-purple-500/20'
    };

    return (
        <div className={`px-2 py-0.5 rounded border text-[9px] font-semibold uppercase tracking-wider ${colors[tier]}`}>
            {label || `TIER ${tier}`}
        </div>
    );
};

export const ConfidenceMeter = ({ value, label = "Confidence" }) => {
    const safeValue = (value === null || value === undefined || isNaN(value)) ? 0 : value;
    const percentage = Math.round(safeValue * 100);

    let color = 'bg-red-500';
    if (percentage > 40) color = 'bg-amber-500';
    if (percentage > 70) color = 'bg-green-500';

    return (
        <div className="space-y-1.5 w-full">
            <div className="flex justify-between items-end">
                <span className="text-[10px] text-neutral-500 font-medium tracking-wide">{label}</span>
                <span className="text-[10px] font-bold text-neutral-300 font-mono">
                    {formatConfidence(value)}
                </span>
            </div>
            <div className="h-1 w-full bg-neutral-800 rounded-full overflow-hidden">
                <div
                    className={`h-full ${color} transition-all duration-1000 ease-out shadow-[0_0_8px_rgba(0,0,0,0.5)]`}
                    style={{ width: `${percentage}%` }}
                />
            </div>
        </div>
    );
};

export const RiskThermometer = ({ severity }) => {
    // severity: 0 (none) to 1 (critical)
    const safeSeverity = (severity === null || severity === undefined || isNaN(severity)) ? 0 : severity;
    const percentage = Math.round(safeSeverity * 100);
    const color = safeSeverity > 0.7 ? 'text-red-400' : safeSeverity > 0.3 ? 'text-amber-400' : 'text-green-400';

    return (
        <div className="flex items-center gap-3">
            <div className="shrink-0 h-14 w-2 rounded-full bg-neutral-800 relative overflow-hidden">
                <div
                    className={`absolute bottom-0 w-full transition-all duration-1000 ${safeSeverity > 0.7 ? 'bg-red-500' : safeSeverity > 0.3 ? 'bg-amber-500' : 'bg-green-500'}`}
                    style={{ height: `${percentage}%` }}
                />
            </div>
            <div className="space-y-0.5">
                <div className="flex items-center gap-1.5">
                    <p className="text-[10px] text-neutral-500 font-medium tracking-wide">Risk Severity</p>
                    <Tooltip text="Measures potential clinical contraindications detected in your medical profile." />
                </div>
                <p className={`text-xs font-bold ${color}`}>
                    {safeSeverity > 0.7 ? 'High / Clinical' : safeSeverity > 0.3 ? 'Moderate / Caution' : 'Low / Minimal'}
                </p>
            </div>
        </div>
    );
};

// EVIDENCE BADGE REMOVED: Strict rendering policies require direct metric display, not heuristic labels.

export const ResponsibleDecision = ({ meta }) => {
    const { decision, reason, tone } = meta;
    const toneColors = {
        positive: 'text-green-400 bg-green-500/5 border-green-500/20',
        negative: 'text-red-400 bg-red-500/5 border-red-500/20',
        neutral: 'text-amber-400 bg-amber-500/5 border-amber-500/20'
    };

    return (
        <div className={`p-4 rounded-lg border flex flex-col items-center text-center gap-2 ${toneColors[tone]} transition-all duration-500 hover:shadow-lg`}>
            <p className="text-[10px] font-medium uppercase tracking-widest opacity-60">Model Inference Decision</p>
            <h4 className="text-sm font-bold tracking-tight uppercase">{decision}</h4>
            <div className="w-8 h-px bg-current opacity-30 my-1"></div>
            <p className="text-[11px] opacity-80 leading-snug max-w-[220px] italic">
                "{reason}"
            </p>
        </div>
    );
};

export const Tooltip = ({ text }) => {
    const [isVisible, setIsVisible] = useState(false);

    return (
        <div className="relative inline-block">
            <HelpCircle
                className="w-3 h-3 text-neutral-600 hover:text-neutral-400 cursor-help transition-colors"
                onMouseEnter={() => setIsVisible(true)}
                onMouseLeave={() => setIsVisible(false)}
            />
            {isVisible && (
                <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 rounded bg-neutral-900 border border-neutral-800 text-[10px] text-neutral-300 shadow-2xl animate-fade-in pointer-events-none">
                    {text}
                    <div className="absolute top-full left-1/2 -translate-x-1/2 border-8 border-transparent border-t-neutral-900"></div>
                </div>
            )}
        </div>
    );
};

export const getConfidenceNarrative = (value) => {
    if (value >= 0.9) return "Absolute confidence derived from specific clinical confirmation.";
    if (value >= 0.7) return "High confidence based on multiple supporting datasets.";
    if (value >= 0.5) return "Moderate confidence based on available interaction data.";
    if (value >= 0.3) return "Potential finding requiring additional verification.";
    return "Low confidence due to significant evidence gaps.";
};

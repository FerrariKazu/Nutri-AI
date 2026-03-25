import React, { useState, useEffect } from 'react';
import { X, AlertTriangle, Link2 } from 'lucide-react';

/**
 * MemoryInsight — Subtle, dismissible insight card rendered below the assistant's response.
 * 
 * Displays two types of insights:
 *   - contradiction: When the current answer conflicts with a past claim
 *   - connection: When the user's question relates to previously explored topics
 * 
 * Design: Non-intrusive, orange-tinted card with smooth entrance/exit animations.
 */
const MemoryInsight = ({ insight, onDismiss }) => {
    const [isVisible, setIsVisible] = useState(false);
    const [isExiting, setIsExiting] = useState(false);

    useEffect(() => {
        if (insight) {
            // Slight delay for entrance animation
            const timer = setTimeout(() => setIsVisible(true), 100);
            return () => clearTimeout(timer);
        }
        setIsVisible(false);
    }, [insight]);

    if (!insight) return null;

    const handleDismiss = () => {
        setIsExiting(true);
        setTimeout(() => {
            setIsExiting(false);
            setIsVisible(false);
            if (onDismiss) onDismiss();
        }, 300);
    };

    const isContradiction = insight.type === 'contradiction';
    const Icon = isContradiction ? AlertTriangle : Link2;

    // Color tokens — warm amber/orange tint
    const borderColor = isContradiction
        ? 'border-amber-500/30'
        : 'border-orange-400/20';
    const bgColor = isContradiction
        ? 'bg-amber-950/40'
        : 'bg-orange-950/30';
    const iconColor = isContradiction
        ? 'text-amber-400'
        : 'text-orange-400';
    const labelColor = isContradiction
        ? 'text-amber-500'
        : 'text-orange-400';

    return (
        <div
            className={`
                max-w-full sm:max-w-4xl mx-auto mt-3 transition-all duration-300 ease-out
                ${isVisible && !isExiting
                    ? 'opacity-100 translate-y-0'
                    : 'opacity-0 translate-y-2'
                }
            `}
            role="complementary"
            aria-label="Memory insight"
        >
            <div className={`
                ${bgColor} ${borderColor}
                border rounded-lg px-4 py-3
                backdrop-blur-sm
                flex items-start gap-3
                group
            `}>
                {/* Icon */}
                <div className={`shrink-0 mt-0.5 ${iconColor}`}>
                    <Icon className="w-4 h-4" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    {/* Label */}
                    <span className={`
                        text-[9px] font-mono uppercase tracking-[0.15em] ${labelColor}
                        block mb-1
                    `}>
                        {isContradiction ? 'Memory — Contradiction Detected' : 'Memory — Topic Connection'}
                    </span>

                    {/* Message */}
                    <p className="text-xs text-neutral-400 leading-relaxed">
                        {insight.message}
                    </p>

                    {/* Past date reference (for contradictions) */}
                    {insight.past_date && (
                        <span className="text-[10px] text-neutral-600 font-mono mt-1.5 block">
                            Referenced: {new Date(insight.past_date).toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric'
                            })}
                        </span>
                    )}
                </div>

                {/* Dismiss */}
                <button
                    onClick={handleDismiss}
                    className="shrink-0 p-1 rounded-md text-neutral-600 hover:text-neutral-400 hover:bg-neutral-800/50 transition-colors opacity-0 group-hover:opacity-100"
                    aria-label="Dismiss insight"
                >
                    <X className="w-3.5 h-3.5" />
                </button>
            </div>
        </div>
    );
};

export default MemoryInsight;

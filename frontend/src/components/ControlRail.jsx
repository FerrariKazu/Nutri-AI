import React from 'react';

/**
 * ControlRail - Vertical segmented control for Analysis Depth.
 * Reframes "modes" as system calibration levels.
 */
const ControlRail = ({ selectedDepth, onDepthChange }) => {
    const depths = [
        { id: 'simple', label: 'Outcome', tooltip: 'Outcome-first analysis' },
        { id: 'standard', label: 'Reasoned', tooltip: 'Standard reasoned synthesis' },
        { id: 'chemistry', label: 'Mechanistic', tooltip: 'Full mechanistic breakdown' },
    ];

    return (
        <div className="flex flex-col gap-8 py-8 px-4 border-r border-neutral-800 h-full bg-neutral-950">
            <div className="flex flex-col gap-1">
                <span className="text-[10px] font-mono uppercase tracking-widest text-neutral-400 mb-4 opacity-50 px-2">
                    Analysis Depth
                </span>
                <div className="flex flex-col gap-2">
                    {depths.map((depth) => (
                        <button
                            key={depth.id}
                            onClick={() => onDepthChange(depth.id)}
                            className={`
                                relative px-3 py-2 text-left transition-all duration-200 group
                                ${selectedDepth === depth.id
                                    ? 'text-accent'
                                    : 'text-neutral-400 hover:text-neutral-100'}
                            `}
                        >
                            {/* Accent Line */}
                            {selectedDepth === depth.id && (
                                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-4 bg-accent" />
                            )}

                            <span className="text-xs font-medium tracking-tight">
                                {depth.label}
                            </span>

                            {/* Subtle hover tooltip or label */}
                            <div className="absolute left-full ml-4 px-2 py-1 bg-neutral-800 text-[10px] rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
                                {depth.tooltip}
                            </div>
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default ControlRail;

import React from 'react';
import { FlaskConical, Zap, Activity, Eye, ChevronRight } from 'lucide-react';

/**
 * PerceptionMapper
 * 
 * Visualizes the Molecule -> Receptor -> Perception chain.
 * Tier 2.5 Feature.
 */
const PerceptionMapper = ({ claim }) => {
    const { receptors = [], sensory_outcomes = [], subject, property } = claim;

    if (receptors.length === 0 && sensory_outcomes.length === 0) {
        return null;
    }

    return (
        <div className="space-y-4 animate-fade-in">
            <div className="flex items-center gap-2">
                <Eye className="w-3.5 h-3.5 text-purple-400" />
                <h4 className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-400">Biological Perception</h4>
            </div>

            <div className="flex items-center gap-2 p-3 rounded-xl bg-purple-500/5 border border-purple-500/10 overflow-hidden relative">
                {/* Connection Line */}
                <div className="absolute left-1/2 top-1/2 -translate-y-1/2 w-full h-px bg-gradient-to-r from-transparent via-purple-500/20 to-transparent -z-10" />

                {/* Molecule */}
                <div className="flex-1 flex flex-col items-center gap-1">
                    <div className="p-1.5 rounded-full bg-neutral-900 border border-purple-500/30">
                        <FlaskConical className="w-3 h-3 text-purple-400" />
                    </div>
                    <span className="text-[9px] font-mono text-neutral-300 uppercase truncate w-full text-center">
                        {subject}
                    </span>
                    {property && (
                        <span className="text-[7px] font-mono text-neutral-600 uppercase">
                            {property}
                        </span>
                    )}
                </div>

                <ChevronRight className="w-3 h-3 text-neutral-700 shrink-0" />

                {/* Receptors */}
                <div className="flex-1 flex flex-col items-center gap-1">
                    <div className="p-1.5 rounded-full bg-neutral-900 border border-purple-500/30">
                        <Zap className="w-3 h-3 text-purple-400" />
                    </div>
                    <div className="flex flex-col items-center">
                        {receptors.length > 0 ? receptors.map((r, i) => (
                            <span key={i} className="text-[9px] font-mono text-neutral-300 uppercase">
                                {r.receptor}
                            </span>
                        )) : (
                            <span className="text-[9px] font-mono text-neutral-600 uppercase italic">Unknown</span>
                        )}
                    </div>
                </div>

                <ChevronRight className="w-3 h-3 text-neutral-700 shrink-0" />

                {/* Perception */}
                <div className="flex-1 flex flex-col items-center gap-1">
                    <div className="p-1.5 rounded-full bg-neutral-900 border border-purple-500/30">
                        <Activity className="w-3 h-3 text-purple-400" />
                    </div>
                    <div className="flex flex-wrap justify-center gap-1">
                        {sensory_outcomes.map((s, i) => (
                            <span key={i} className="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 text-[8px] font-bold uppercase">
                                {s}
                            </span>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default PerceptionMapper;

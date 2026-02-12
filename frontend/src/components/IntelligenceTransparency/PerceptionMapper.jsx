import React from 'react';
import { FlaskConical, Zap, Activity, Eye, ChevronRight, TrendingUp, TrendingDown, Clock, HelpCircle } from 'lucide-react';

/**
 * PerceptionMapper v1.2
 * 
 * Visualizes the Molecule -> [Receptor] -> Perception chain.
 * Supports multi-family outputs (Chemical, Process, Physical, Structural).
 */
const PerceptionMapper = ({ claim }) => {
    const { receptors = [], perception_outputs = [], compounds = [] } = claim;

    const directionIcons = {
        'increase': <TrendingUp className="w-2.5 h-2.5 text-blue-400" />,
        'decrease': <TrendingDown className="w-2.5 h-2.5 text-amber-500" />,
        'delay': <Clock className="w-2.5 h-2.5 text-purple-400" />,
        'neutral': <HelpCircle className="w-2.5 h-2.5 text-neutral-500" />
    };

    return (
        <div className="space-y-4 animate-fade-in">
            <div className="flex items-center gap-2">
                <Eye className="w-3.5 h-3.5 text-purple-400" />
                <h4 className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-400">Biological Perception</h4>
            </div>

            <div className="flex items-center gap-2 p-3 rounded-xl bg-purple-500/5 border border-purple-500/10 overflow-hidden relative">
                {/* Connection Line */}
                <div className="absolute left-1/2 top-1/2 -translate-y-1/2 w-full h-px bg-gradient-to-r from-transparent via-purple-500/20 to-transparent -z-10" />

                {/* Compounds / Stimuli */}
                <div className="flex-1 flex flex-col items-center gap-1">
                    <div className="p-1.5 rounded-full bg-neutral-900 border border-purple-500/30">
                        <FlaskConical className="w-3 h-3 text-purple-400" />
                    </div>
                    <div className="flex flex-col items-center">
                        {compounds.length > 0 ? compounds.map((c, i) => (
                            <span key={i} className="text-[9px] font-mono text-neutral-300 uppercase truncate w-full text-center">
                                {c.replace(/_/g, ' ')}
                            </span>
                        )) : (
                            <span className="text-[9px] font-mono text-neutral-300 uppercase">Stimulus</span>
                        )}
                    </div>
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
                                {r}
                            </span>
                        )) : (
                            <span className="text-[9px] font-mono text-neutral-600 uppercase italic">Indirect</span>
                        )}
                    </div>
                </div>

                <ChevronRight className="w-3 h-3 text-neutral-700 shrink-0" />

                {/* Perceptions / Outcomes */}
                <div className="flex-1 flex flex-col items-center gap-1">
                    <div className="p-1.5 rounded-full bg-neutral-900 border border-purple-500/30">
                        <Activity className="w-3 h-3 text-purple-400" />
                    </div>
                    <div className="flex flex-wrap justify-center gap-1">
                        {perception_outputs.map((p, i) => (
                            <div key={i} className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-purple-500/20 border border-purple-500/30">
                                <span className="text-purple-300 text-[8px] font-bold uppercase whitespace-nowrap">
                                    {p.label}
                                </span>
                                {directionIcons[p.direction]}
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default PerceptionMapper;

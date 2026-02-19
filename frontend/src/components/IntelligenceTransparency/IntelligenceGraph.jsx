import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Beaker, Target, Activity, ChevronRight } from 'lucide-react';

/**
 * IntelligenceGraph
 * 
 * [MANDATE] Deterministic Molecule -> Receptor -> Perception UI
 * Visualizes the reasoning chain as a directed graph.
 */
const IntelligenceGraph = ({ trace, claim }) => {
    const isMechanistic = trace?.trace_variant === 'mechanistic';
    const graph = trace?.graph || {};

    // 🔬 [MECHANISTIC_V2] Dynamic Graph Rendering
    if (isMechanistic) {
        if (!graph.nodes || graph.nodes.length < 3) {
            console.error("[GRAPH_ERROR] Mechanistic trace missing required nodes.", graph);
            return (
                <div className="p-6 border border-red-500/20 bg-red-500/5 rounded-xl">
                    <div className="flex items-center gap-2 mb-2 text-red-400">
                        <AlertTriangle className="w-4 h-4" />
                        <span className="text-xs font-bold uppercase">Mechanism Contract Violation</span>
                    </div>
                    <p className="text-[10px] text-red-400/80 font-mono">
                        Trace mandated variant "mechanistic" but graph payload is under-populated.
                        Source component failed to synthesize 3-tier causal chain.
                    </p>
                </div>
            );
        }

        // Group nodes by type for structured layout
        const nodesByType = graph.nodes.reduce((acc, node) => {
            const type = node.type || 'other';
            if (!acc[type]) acc[type] = [];
            acc[type].push(node);
            return acc;
        }, {});

        return (
            <div className="space-y-8">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
                    <div className="flex items-center gap-2">
                        <Activity className="w-3.5 h-3.5 text-accent" />
                        <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest text-neutral-400">
                            Dynamic Mechanistic Topology
                        </h4>
                    </div>
                    <span className="text-[8px] font-mono text-purple-400 px-1.5 py-0.5 rounded border border-purple-500/20 bg-purple-500/5">
                        GENERATIVE_CAUSALITY_v2.0
                    </span>
                </div>

                {/* Structured Causal View */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
                    {/* Layer 1: Molecular/Compounds */}
                    <div className="space-y-4">
                        <div className="text-[9px] font-mono text-neutral-600 uppercase tracking-tighter text-center">Molecular Basis</div>
                        {(nodesByType.compound || nodesByType.molecular || []).map((node, i) => (
                            <Node
                                key={node.id}
                                icon={<Beaker className="w-3 h-3 text-purple-400" />}
                                label={node.label}
                                color="purple"
                            />
                        ))}
                    </div>

                    {/* Layer 2: Mechanisms/Processes */}
                    <div className="space-y-4">
                        <div className="text-[9px] font-mono text-neutral-600 uppercase tracking-tighter text-center">Causal Mechanism</div>
                        {(nodesByType.mechanism || nodesByType.process || []).map((node, i) => (
                            <Node
                                key={node.id}
                                icon={<Target className="w-3 h-3 text-orange-400" />}
                                label={node.label}
                                color="orange"
                            />
                        ))}
                    </div>

                    {/* Layer 3: Perception/Surface */}
                    <div className="space-y-4">
                        <div className="text-[9px] font-mono text-neutral-600 uppercase tracking-tighter text-center">Surface Effect</div>
                        {(nodesByType.perception || nodesByType.surface || []).map((node, i) => (
                            <Node
                                key={node.id}
                                icon={<Activity className="w-3 h-3 text-blue-400" />}
                                label={node.label}
                                color="blue"
                            />
                        ))}
                    </div>
                </div>

                <div className="flex flex-wrap gap-4 justify-center items-center opacity-40">
                    <div className="flex items-center gap-2">
                        <div className="w-4 h-px bg-neutral-400" />
                        <span className="text-[8px] font-mono uppercase">Direct Causal Link</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-4 h-px bg-neutral-400 border-dashed border-t" />
                        <span className="text-[8px] font-mono uppercase">Theoretical Influence</span>
                    </div>
                </div>
            </div>
        );
    }

    // ──────────────────────────────
    // 🏛️ LEGACY TEMPLATE (Fallback)
    // ──────────────────────────────
    const compounds = claim.compounds || [];
    const receptors = claim.receptors || [];
    const perception_outputs = claim.perception_outputs || [];

    console.log(`[GRAPH_PAINT] Rendering legacy topology for ${claim.id}`);

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-2 mb-4">
                <Activity className="w-3.5 h-3.5 text-accent" />
                <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest text-neutral-400">
                    Mechanism Topology (Legacy)
                </h4>
            </div>

            <div className="flex flex-col md:flex-row items-center justify-between gap-6 relative">
                <div className="flex flex-col gap-3 w-full md:w-1/3">
                    <span className="text-[9px] font-mono text-neutral-600 uppercase tracking-tighter text-center">Compounds</span>
                    {compounds.length > 0 ? compounds.map((c, i) => (
                        <Node key={i} icon={<Beaker className="w-3 h-3 text-green-400" />} label={c} color="green" />
                    )) : <EmptyNode label="Unspecified" />}
                </div>

                <div className="hidden md:block"><Connector /></div>

                <div className="flex flex-col gap-3 w-full md:w-1/3">
                    <span className="text-[9px] font-mono text-neutral-600 uppercase tracking-tighter text-center">Receptors</span>
                    {receptors.length > 0 ? receptors.map((r, i) => (
                        <Node key={i} icon={<Target className="w-3 h-3 text-blue-400" />} label={r} color="blue" />
                    )) : <EmptyNode label="Theoretical" />}
                </div>

                <div className="hidden md:block"><Connector /></div>

                <div className="flex flex-col gap-3 w-full md:w-1/3">
                    <span className="text-[9px] font-mono text-neutral-600 uppercase tracking-tighter text-center">Perception</span>
                    {perception_outputs.length > 0 ? perception_outputs.map((p, i) => (
                        <Node
                            key={i}
                            icon={<Activity className="w-3 h-3 text-amber-400" />}
                            label={p.description || p.modality}
                            color="amber"
                            subtitle={p.receptor}
                        />
                    )) : <EmptyNode label="Unknown" />}
                </div>
            </div>

            <p className="text-[9px] text-neutral-600 italic text-center mt-4">
                * Solid lines indicate PubChem-verified paths. Dashed lines indicate theoretical associations.
            </p>
        </div>
    );
};

const Node = ({ icon, label, color, subtitle }) => {
    const colors = {
        green: "bg-green-500/10 border-green-500/20 text-green-200",
        blue: "bg-blue-500/10 border-blue-500/20 text-blue-200",
        amber: "bg-amber-500/10 border-amber-500/20 text-amber-100"
    };

    return (
        <motion.div
            whileHover={{ scale: 1.01, y: -1 }}
            className={`flex flex-col p-3 rounded-lg border shadow-sm ${colors[color]} backdrop-blur-md relative group`}
        >
            <div className="flex items-center gap-3">
                <div className="shrink-0 p-1.5 rounded bg-black/40 border border-white/5">
                    {icon}
                </div>
                <div className="flex flex-col">
                    <span className="text-[11px] font-semibold font-mono tracking-tight uppercase">{label}</span>
                    {subtitle && <span className="text-[8px] font-mono opacity-60 uppercase tracking-tight">via {subtitle}</span>}
                </div>
            </div>
        </motion.div>
    );
};

const EmptyNode = ({ label }) => (
    <div className="p-3 rounded-lg border border-neutral-800 bg-neutral-900/20 border-dashed text-center">
        <span className="text-[10px] font-mono text-neutral-700 uppercase italic">{label}</span>
    </div>
);

const Connector = () => (
    <div className="flex items-center justify-center opacity-20">
        <div className="w-8 h-px bg-neutral-100" />
        <ChevronRight className="w-3 h-3 text-neutral-100" />
    </div>
);

export default IntelligenceGraph;

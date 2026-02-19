import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Beaker, Target, Activity, ChevronRight } from 'lucide-react';

/**
 * IntelligenceGraph
 * 
 * [MANDATE] Deterministic Molecule -> Receptor -> Perception UI
 * Visualizes the reasoning chain as a directed graph.
 */
const IntelligenceGraph = ({ trace }) => {
    const graph = trace?.graph || { nodes: [], edges: [] };

    // 🧬 [AUTO_LAYOUT] Topological Layering based on causality depth
    const layers = useMemo(() => {
        if (!graph.nodes || graph.nodes.length === 0) return [];

        const nodeMap = new Map(graph.nodes.map(n => [n.id, n]));
        const adj = new Map();
        const inDegree = new Map(graph.nodes.map(n => [n.id, 0]));

        (graph.edges || []).forEach(e => {
            if (!adj.has(e.source)) adj.set(e.source, []);
            adj.get(e.source).push(e.target);
            inDegree.set(e.target, (inDegree.get(e.target) || 0) + 1);
        });

        const sortedLayers = [];
        let currentLevel = graph.nodes.filter(n => (inDegree.get(n.id) || 0) === 0);
        const seen = new Set();

        while (currentLevel.length > 0) {
            sortedLayers.push(currentLevel);
            currentLevel.forEach(n => seen.add(n.id));

            const nextLevel = [];
            currentLevel.forEach(node => {
                (adj.get(node.id) || []).forEach(childId => {
                    inDegree.set(childId, inDegree.get(childId) - 1);
                    if (inDegree.get(childId) === 0 && !seen.has(childId)) {
                        nextLevel.push(nodeMap.get(childId));
                    }
                });
            });
            currentLevel = nextLevel;
        }

        // Catch orphans/cycles
        const layeredIds = new Set(seen);
        const orphans = graph.nodes.filter(n => !layeredIds.has(n.id));
        if (orphans.length > 0) sortedLayers.push(orphans);

        return sortedLayers;
    }, [graph]);

    if (!graph.nodes || graph.nodes.length === 0) {
        return (
            <div className="p-8 border border-dashed border-neutral-800 rounded-xl flex flex-col items-center justify-center opacity-30">
                <Activity className="w-8 h-8 mb-2" />
                <span className="text-[10px] font-mono tracking-[0.2em] uppercase">No causal topology available</span>
            </div>
        );
    }

    return (
        <div className="space-y-12">
            <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
                <div className="flex items-center gap-2">
                    <Activity className="w-3.5 h-3.5 text-accent" />
                    <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest text-neutral-400">
                        Mechanism Topology
                    </h4>
                </div>
                {trace.trace_variant === "mechanistic" && (
                    <span className="text-[8px] font-mono text-purple-400 px-1.5 py-0.5 rounded border border-purple-500/20 bg-purple-500/5">
                        MECHANISTIC_CAUSALITY_v2.0
                    </span>
                )}
            </div>

            {/* Dynamic Graph Grid */}
            <div className="flex items-start justify-between gap-x-[220px] relative overflow-x-auto pb-8 pt-4 scrollbar-thin scrollbar-thumb-neutral-800">
                {layers.map((layer, lIdx) => (
                    <div key={lIdx} className="flex flex-col items-center gap-y-[120px] shrink-0 min-w-[200px]">
                        {layer.map((node, nIdx) => (
                            <div key={node.id} className="relative w-full">
                                <Node
                                    icon={node.type === 'compound' ? <Beaker className="w-3.5 h-3.5" /> :
                                        node.type === 'mechanism' ? <Target className="w-3.5 h-3.5" /> :
                                            <Activity className="w-3.5 h-3.5" />}
                                    label={node.label}
                                    type={node.type}
                                    verified={node.verified}
                                />
                                {/* Simplified causal connector to the next layer */}
                                {lIdx < layers.length - 1 && (
                                    <div className="absolute top-1/2 -right-[110px] w-[110px] h-px bg-neutral-800 hidden lg:block" />
                                )}
                            </div>
                        ))}
                    </div>
                ))}
            </div>

            <div className="flex flex-wrap gap-4 justify-center items-center opacity-40">
                <div className="flex items-center gap-2">
                    <div className="w-4 h-px bg-neutral-400" />
                    <span className="text-[8px] font-mono uppercase tracking-tighter">Causal Link</span>
                </div>
                {layers.length > 2 && (
                    <div className="flex items-center gap-2">
                        <ChevronRight className="w-3 h-3 text-neutral-400" />
                        <span className="text-[8px] font-mono uppercase tracking-tighter">Propagation Direction</span>
                    </div>
                )}
            </div>
        </div>
    );
};

const Node = ({ icon, label, type, verified }) => {
    const typeStyles = {
        compound: "border-purple-500/30 text-purple-200 bg-purple-500/5 shadow-[0_0_15px_rgba(168,85,247,0.1)]",
        mechanism: "border-orange-500/30 text-orange-200 bg-orange-500/5 shadow-[0_0_15px_rgba(249,115,22,0.1)]",
        perception: "border-blue-500/30 text-blue-200 bg-blue-500/5 shadow-[0_0_15px_rgba(59,130,246,0.1)]",
        other: "border-neutral-700 text-neutral-300 bg-neutral-900/50"
    };

    return (
        <motion.div
            whileHover={{ scale: 1.02, y: -2 }}
            className={`node-card group relative p-4 rounded-xl border backdrop-blur-md transition-shadow ${typeStyles[type] || typeStyles.other}`}
        >
            <div className="flex items-start gap-3">
                <div className="p-2 rounded -lg bg-black/40 border border-white/5 shrink-0">
                    {icon}
                </div>
                <div className="flex flex-col min-w-0 pr-2">
                    <span className="text-[11px] font-bold font-mono tracking-tight uppercase leading-tight truncate">
                        {label}
                    </span>
                    <div className="flex items-center gap-1.5 mt-1">
                        <span className="text-[8px] font-mono opacity-50 uppercase tracking-widest">{type}</span>
                        {verified && (
                            <div className="w-1 h-1 rounded-full bg-green-500 shadow-[0_0_5px_rgba(34,197,94,0.5)]" />
                        )}
                    </div>
                </div>
            </div>

            {/* Hover Indicator */}
            <div className="absolute -inset-px rounded-xl opacity-0 group-hover:opacity-100 transition-opacity bg-white/[0.02] pointer-events-none" />
        </motion.div>
    );
};

const EmptyNode = () => null;
const Connector = () => null;

export default IntelligenceGraph;

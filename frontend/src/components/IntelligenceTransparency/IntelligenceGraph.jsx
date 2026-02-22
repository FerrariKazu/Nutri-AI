import React, { useMemo, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Beaker, Target, Activity, X, Zap, Eye, Layers } from 'lucide-react';

/**
 * NODE_COLORS — domain-aware color system for the topology graph.
 */
const NODE_COLORS = {
    surface: { bg: 'bg-blue-500/8', border: 'border-blue-500/30', text: 'text-blue-200', dot: 'bg-blue-400', shadow: 'shadow-[0_0_15px_rgba(59,130,246,0.1)]' },
    process: { bg: 'bg-orange-500/8', border: 'border-orange-500/30', text: 'text-orange-200', dot: 'bg-orange-400', shadow: 'shadow-[0_0_15px_rgba(249,115,22,0.1)]' },
    molecular: { bg: 'bg-purple-500/8', border: 'border-purple-500/30', text: 'text-purple-200', dot: 'bg-purple-400', shadow: 'shadow-[0_0_15px_rgba(168,85,247,0.1)]' },
    compound: { bg: 'bg-emerald-500/8', border: 'border-emerald-500/30', text: 'text-emerald-200', dot: 'bg-emerald-400', shadow: 'shadow-[0_0_15px_rgba(16,185,129,0.1)]' },
    mechanism: { bg: 'bg-red-500/8', border: 'border-red-500/30', text: 'text-red-200', dot: 'bg-red-400', shadow: 'shadow-[0_0_15px_rgba(239,68,68,0.1)]' },
    perception: { bg: 'bg-yellow-500/8', border: 'border-yellow-500/30', text: 'text-yellow-200', dot: 'bg-yellow-400', shadow: 'shadow-[0_0_15px_rgba(234,179,8,0.1)]' },
    other: { bg: 'bg-neutral-800/30', border: 'border-neutral-700', text: 'text-neutral-300', dot: 'bg-neutral-500', shadow: '' },
};

const getNodeType = (node) => {
    const t = (node.type || node.domain || '').toLowerCase();
    if (t.includes('surface')) return 'surface';
    if (t.includes('process')) return 'process';
    if (t.includes('molecular') || t.includes('molecule')) return 'molecular';
    if (t.includes('compound')) return 'compound';
    if (t.includes('mechanism')) return 'mechanism';
    if (t.includes('perception')) return 'perception';
    return 'other';
};

/**
 * Node Detail Modal — shown on click.
 */
const NodeDetailModal = ({ node, edges, onClose }) => {
    if (!node) return null;

    const connectedEdges = (edges || []).filter(e => e.source === node.id || e.target === node.id);
    const colors = NODE_COLORS[getNodeType(node)] || NODE_COLORS.other;

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={onClose}
        >
            <motion.div
                initial={{ scale: 0.9, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.9, y: 20 }}
                className={`relative w-full max-w-sm bg-neutral-950 border ${colors.border} rounded-xl p-5 space-y-4 ${colors.shadow}`}
                onClick={e => e.stopPropagation()}
            >
                <button onClick={onClose} className="absolute top-3 right-3 text-neutral-500 hover:text-neutral-300 transition-colors">
                    <X className="w-4 h-4" />
                </button>
                <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${colors.bg} ${colors.border} border`}>
                        {getNodeType(node) === 'compound' ? <Beaker className="w-4 h-4" /> :
                            getNodeType(node) === 'mechanism' ? <Target className="w-4 h-4" /> :
                                <Activity className="w-4 h-4" />}
                    </div>
                    <div>
                        <h3 className={`text-sm font-bold uppercase tracking-tight ${colors.text}`}>{node.label}</h3>
                        <span className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest">{node.type || node.domain || 'unknown'}</span>
                    </div>
                </div>

                {node.description && (
                    <p className="text-[11px] text-neutral-400 leading-relaxed">{node.description}</p>
                )}

                <div className="grid grid-cols-2 gap-3 text-[10px]">
                    {node.domain && (
                        <div>
                            <span className="text-[8px] text-neutral-600 uppercase tracking-wider font-semibold">Domain</span>
                            <p className="text-neutral-300 font-mono">{node.domain}</p>
                        </div>
                    )}
                    {node.confidence != null && (
                        <div>
                            <span className="text-[8px] text-neutral-600 uppercase tracking-wider font-semibold">Confidence</span>
                            <p className="text-neutral-300 font-mono">{Math.round(node.confidence * 100)}%</p>
                        </div>
                    )}
                </div>

                {connectedEdges.length > 0 && (
                    <div className="pt-3 border-t border-neutral-800/50 space-y-2">
                        <span className="text-[8px] font-bold text-neutral-600 uppercase tracking-widest">Connected Edges ({connectedEdges.length})</span>
                        <div className="space-y-1 max-h-32 overflow-y-auto">
                            {connectedEdges.map((edge, i) => (
                                <div key={i} className="flex items-center gap-2 text-[9px] font-mono text-neutral-500 bg-neutral-900/50 px-2 py-1.5 rounded">
                                    <span className="text-neutral-400">{edge.source}</span>
                                    <span className="text-neutral-600">→</span>
                                    <span className="text-neutral-400">{edge.target}</span>
                                    {edge.label && <span className="text-neutral-600 ml-auto text-[8px]">{edge.label}</span>}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </motion.div>
        </motion.div>
    );
};

/**
 * Color Legend Bar.
 */
const ColorLegend = () => (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 justify-center items-center py-2">
        {[
            { label: 'Surface', color: 'bg-blue-400' },
            { label: 'Process', color: 'bg-orange-400' },
            { label: 'Molecular', color: 'bg-purple-400' },
            { label: 'Compound', color: 'bg-emerald-400' },
            { label: 'Mechanism', color: 'bg-red-400' },
            { label: 'Perception', color: 'bg-yellow-400' },
        ].map(item => (
            <div key={item.label} className="flex items-center gap-1.5">
                <div className={`w-2 h-2 rounded-full ${item.color}`} />
                <span className="text-[8px] font-mono uppercase tracking-tighter text-neutral-500">{item.label}</span>
            </div>
        ))}
    </div>
);

/**
 * Node Component
 */
const Node = ({ node, onClick }) => {
    const type = getNodeType(node);
    const colors = NODE_COLORS[type];
    const icon = type === 'compound' ? <Beaker className="w-3.5 h-3.5" /> :
        type === 'mechanism' ? <Target className="w-3.5 h-3.5" /> :
            <Activity className="w-3.5 h-3.5" />;

    return (
        <motion.div
            whileHover={{ scale: 1.03, y: -2 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onClick(node)}
            className={`node-card group relative p-3 md:p-4 rounded-xl border backdrop-blur-md transition-shadow cursor-pointer ${colors.bg} ${colors.border} ${colors.text} ${colors.shadow}`}
        >
            <div className="flex items-start gap-2 md:gap-3">
                <div className="p-1.5 md:p-2 rounded-lg bg-black/40 border border-white/5 shrink-0">
                    {icon}
                </div>
                <div className="flex flex-col min-w-0 pr-1 md:pr-2">
                    <span className="text-[10px] md:text-[11px] font-bold font-mono tracking-tight uppercase leading-tight line-clamp-2">
                        {node.label}
                    </span>
                    <div className="flex items-center gap-1.5 mt-1">
                        <span className="text-[7px] md:text-[8px] font-mono opacity-50 uppercase tracking-widest">{node.type || 'node'}</span>
                        {node.verified && (
                            <div className="w-1 h-1 rounded-full bg-green-500 shadow-[0_0_5px_rgba(34,197,94,0.5)]" />
                        )}
                        {node.confidence != null && (
                            <span className="text-[7px] font-mono opacity-40">{Math.round(node.confidence * 100)}%</span>
                        )}
                    </div>
                </div>
            </div>
            <div className="absolute -inset-px rounded-xl opacity-0 group-hover:opacity-100 transition-opacity bg-white/[0.02] pointer-events-none" />
        </motion.div>
    );
};

/**
 * IntelligenceGraph (v1.2.8)
 * 
 * Deterministic topology visualization with mobile responsiveness.
 */
const IntelligenceGraph = React.memo(({ trace }) => {
    const graph = trace?.graph || { nodes: [], edges: [] };
    const [selectedNode, setSelectedNode] = useState(null);

    const handleNodeClick = useCallback((node) => setSelectedNode(node), []);
    const handleCloseModal = useCallback(() => setSelectedNode(null), []);

    // Topological layering
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
        <div className="space-y-6">
            <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
                <div className="flex items-center gap-2">
                    <Layers className="w-3.5 h-3.5 text-accent" />
                    <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest text-neutral-400">
                        Mechanism Topology
                    </h4>
                </div>
                <span className="text-[8px] font-mono text-neutral-600">
                    {graph.nodes.length} nodes • {(graph.edges || []).length} edges
                </span>
            </div>

            {/* Color Legend */}
            <ColorLegend />

            {/* Dynamic Graph Grid — responsive */}
            <div className="flex flex-col md:flex-row items-start justify-between gap-y-6 md:gap-x-16 relative overflow-x-auto pb-4 pt-2 scrollbar-thin scrollbar-thumb-neutral-800">
                {layers.map((layer, lIdx) => (
                    <div key={lIdx} className="flex flex-row md:flex-col items-center gap-3 md:gap-y-8 shrink-0 w-full md:w-auto md:min-w-[180px]">
                        {layer.map((node) => (
                            <div key={node.id} className="relative w-full md:w-auto">
                                <Node node={node} onClick={handleNodeClick} />
                                {lIdx < layers.length - 1 && (
                                    <div className="absolute top-1/2 -right-8 w-8 h-px bg-neutral-800 hidden lg:block" />
                                )}
                            </div>
                        ))}
                    </div>
                ))}
            </div>

            {/* Node Detail Modal */}
            <AnimatePresence>
                {selectedNode && (
                    <NodeDetailModal
                        node={selectedNode}
                        edges={graph.edges}
                        onClose={handleCloseModal}
                    />
                )}
            </AnimatePresence>
        </div>
    );
});

export default IntelligenceGraph;

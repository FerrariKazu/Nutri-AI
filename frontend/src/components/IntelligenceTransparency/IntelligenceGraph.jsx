import React, { useMemo, useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Beaker, Target, Activity, X, Zap, Eye, Layers } from 'lucide-react';
import { NODE_RADIUS, calculateEdgeOffsets } from './GraphUtils';

/**
 * NODE_COLORS — domain-aware color system (v1.2.9)
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
 * Node Detail Modal
 */
const NodeDetailModal = ({ node, edges, onClose }) => {
    if (!node) return null;
    const connectedEdges = (edges || []).filter(e => e.source === node.id || e.target === node.id);
    const type = getNodeType(node);
    const colors = NODE_COLORS[type] || NODE_COLORS.other;

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4"
            onClick={onClose}
        >
            <motion.div
                initial={{ scale: 0.9, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.9, y: 20 }}
                className={`relative w-full max-w-sm intelligence-glass p-5 space-y-4 border ${colors.border} ${colors.shadow}`}
                onClick={e => e.stopPropagation()}
            >
                <button onClick={onClose} className="absolute top-3 right-3 text-neutral-500 hover:text-neutral-300 transition-colors">
                    <X className="w-4 h-4" />
                </button>
                <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${colors.bg} ${colors.border} border`}>
                        {type === 'compound' ? <Beaker className="w-4 h-4" /> :
                            type === 'mechanism' ? <Target className="w-4 h-4" /> :
                                <Activity className="w-4 h-4" />}
                    </div>
                    <div>
                        <h3 className={`text-sm font-bold uppercase tracking-tight ${colors.text}`}>{node.label}</h3>
                        <span className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest">{node.type || node.domain || 'unknown'}</span>
                    </div>
                </div>
                {node.description && <p className="text-[11px] text-neutral-400 leading-relaxed">{node.description}</p>}
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
            </motion.div>
        </motion.div>
    );
};

/**
 * Node Component
 */
const Node = React.forwardRef(({ node, onClick }, ref) => {
    const type = getNodeType(node);
    const colors = NODE_COLORS[type];
    const icon = type === 'compound' ? <Beaker className="w-3.5 h-3.5" /> :
        type === 'mechanism' ? <Target className="w-3.5 h-3.5" /> :
            <Activity className="w-3.5 h-3.5" />;

    return (
        <motion.div
            ref={ref}
            whileHover={{ scale: 1.03, y: -2 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onClick(node)}
            style={{ width: NODE_RADIUS * 2 * 3, height: NODE_RADIUS * 2.5 }} // Responsive constraints
            className={`group relative p-3 rounded-xl border backdrop-blur-md transition-shadow cursor-pointer flex items-center justify-center ${colors.bg} ${colors.border} ${colors.text} ${colors.shadow}`}
        >
            <div className="flex items-center gap-3 min-w-0 w-full">
                <div className="p-1.5 rounded-lg bg-black/40 border border-white/5 shrink-0">
                    {icon}
                </div>
                <div className="flex flex-col min-w-0 flex-1">
                    <span className="text-[10px] font-bold font-mono tracking-tight uppercase leading-tight truncate">
                        {node.label}
                    </span>
                    <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[7px] font-mono opacity-50 uppercase tracking-widest truncate">{node.type || 'node'}</span>
                        {node.verified && <div className="w-1 h-1 rounded-full bg-green-500 shadow-[0_0_5px_rgba(34,197,94,0.5)] shrink-0" />}
                    </div>
                </div>
            </div>
        </motion.div>
    );
});

/**
 * IntelligenceGraph (v1.2.9)
 */
const IntelligenceGraph = React.memo(({ trace }) => {
    const graph = useMemo(() => trace?.graph || { nodes: [], edges: [] }, [trace]);
    const [selectedNode, setSelectedNode] = useState(null);
    const containerRef = useRef(null);
    const nodeRefs = useRef({});

    const handleNodeClick = useCallback((node) => setSelectedNode(node), []);
    const handleCloseModal = useCallback(() => setSelectedNode(null), []);

    // Layout Layering
    const layers = useMemo(() => {
        if (!graph.nodes?.length) return [];
        const nodeMap = new Map(graph.nodes.map(n => [n.id, n]));
        const inDegree = new Map(graph.nodes.map(n => [n.id, 0]));
        const adj = new Map();

        graph.edges?.forEach(e => {
            if (!adj.has(e.source)) adj.set(e.source, []);
            adj.get(e.source).push(e.target);
            inDegree.set(e.target, (inDegree.get(e.target) || 0) + 1);
        });

        const sortedLayers = [];
        let current = graph.nodes.filter(n => (inDegree.get(n.id) || 0) === 0);
        const seen = new Set();

        while (current.length > 0) {
            sortedLayers.push(current);
            current.forEach(n => seen.add(n.id));
            const next = [];
            current.forEach(n => {
                adj.get(n.id)?.forEach(t => {
                    inDegree.set(t, inDegree.get(t) - 1);
                    if (inDegree.get(t) === 0 && !seen.has(t)) next.push(nodeMap.get(t));
                });
            });
            current = next;
        }
        return sortedLayers;
    }, [graph]);

    const [edgePaths, setEdgePaths] = useState([]);

    // Calculate Edge Geometries
    useEffect(() => {
        if (!containerRef.current || !layers.length) return;

        const updateEdges = () => {
            const containerRect = containerRef.current.getBoundingClientRect();
            const paths = [];

            graph.edges?.forEach(edge => {
                const srcEl = nodeRefs.current[edge.source];
                const dstEl = nodeRefs.current[edge.target];
                if (!srcEl || !dstEl) return;

                const srcRect = srcEl.getBoundingClientRect();
                const dstRect = dstEl.getBoundingClientRect();

                const x1 = (srcRect.left + srcRect.width / 2) - containerRect.left;
                const y1 = (srcRect.top + srcRect.height / 2) - containerRect.top;
                const x2 = (dstRect.left + dstRect.width / 2) - containerRect.left;
                const y2 = (dstRect.top + dstRect.height / 2) - containerRect.top;

                const { x1_off, y1_off, x2_off, y2_off } = calculateEdgeOffsets(x1, y1, x2, y2);
                paths.push({ x1: x1_off, y1: y1_off, x2: x2_off, y2: y2_off });
            });
            setEdgePaths(paths);
        };

        updateEdges();
        window.addEventListener('resize', updateEdges);
        return () => window.removeEventListener('resize', updateEdges);
    }, [layers, graph.edges]);

    if (!graph.nodes?.length) return (
        <div className="p-8 border border-dashed border-neutral-800 rounded-xl flex flex-col items-center justify-center opacity-30">
            <Activity className="w-8 h-8 mb-2" />
            <span className="text-[10px] font-mono uppercase tracking-[0.2em]">No Topology Data</span>
        </div>
    );

    return (
        <div className="space-y-6" key={trace?.trace_id || 'static'}>
            <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
                <div className="flex items-center gap-2">
                    <Layers className="w-3.5 h-3.5 text-accent" />
                    <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest text-neutral-400">Mechanism Topology</h4>
                </div>
                <span className="text-[8px] font-mono text-neutral-600">{graph.nodes.length} nodes • {graph.edges?.length || 0} edges</span>
            </div>

            <div ref={containerRef} className="relative overflow-visible min-h-[400px]">
                {/* SVG Edge Layer — Behind Nodes */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
                    <defs>
                        <marker id="arrowhead"
                            markerUnits="strokeWidth"
                            orient="auto"
                            markerWidth="6"
                            markerHeight="6"
                            refX="6"
                            refY="3"
                        >
                            <path d="M0,0 L6,3 L0,6 Z" fill="#4b5563" />
                        </marker>
                    </defs>
                    {edgePaths.map((p, i) => (
                        <line
                            key={i}
                            x1={p.x1} y1={p.y1} x2={p.x2} y2={p.y2}
                            stroke="#374151"
                            strokeWidth="1.5"
                            markerEnd="url(#arrowhead)"
                        />
                    ))}
                </svg>

                {/* Node Layer — Interactive */}
                <div className="relative z-10 flex flex-col md:flex-row items-center justify-around gap-12 py-8">
                    {layers.map((layer, lIdx) => (
                        <div key={lIdx} className="flex flex-row md:flex-col gap-6">
                            {layer.map(node => (
                                <Node
                                    key={node.id}
                                    node={node}
                                    onClick={handleNodeClick}
                                    ref={el => nodeRefs.current[node.id] = el}
                                />
                            ))}
                        </div>
                    ))}
                </div>
            </div>

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

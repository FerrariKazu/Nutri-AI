import React, { useMemo, useRef, useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Target, Activity, Zap, Beaker } from 'lucide-react';
import { NODE_RADIUS, calculateEdgeOffsets } from './GraphUtils';

/**
 * CausalityGraph (v1.2.9)
 * 
 * Deterministic horizontal chain renderer for linear causal logic.
 * A → B → C flow.
 */
const CausalityGraph = React.memo(({ chain }) => {
    const containerRef = useRef(null);
    const nodeRefs = useRef({});
    const [edgePaths, setEdgePaths] = useState([]);

    const nodes = useMemo(() => chain || [], [chain]);

    useEffect(() => {
        if (!containerRef.current || nodes.length < 2) return;

        const updateEdges = () => {
            const containerRect = containerRef.current.getBoundingClientRect();
            const paths = [];

            for (let i = 0; i < nodes.length - 1; i++) {
                const src = nodes[i];
                const dst = nodes[i + 1];
                const srcEl = nodeRefs.current[src.id || i];
                const dstEl = nodeRefs.current[dst.id || (i + 1)];

                if (!srcEl || !dstEl) continue;

                const srcRect = srcEl.getBoundingClientRect();
                const dstRect = dstEl.getBoundingClientRect();

                const x1 = (srcRect.left + srcRect.width / 2) - containerRect.left;
                const y1 = (srcRect.top + srcRect.height / 2) - containerRect.top;
                const x2 = (dstRect.left + dstRect.width / 2) - containerRect.left;
                const y2 = (dstRect.top + dstRect.height / 2) - containerRect.top;

                const { x1_off, y1_off, x2_off, y2_off } = calculateEdgeOffsets(x1, y1, x2, y2);
                paths.push({ x1: x1_off, y1: y1_off, x2: x2_off, y2: y2_off });
            }
            setEdgePaths(paths);
        };

        updateEdges();
        window.addEventListener('resize', updateEdges);
        return () => window.removeEventListener('resize', updateEdges);
    }, [nodes]);

    if (!nodes.length) return null;

    return (
        <div className="intelligence-glass p-6 overflow-x-auto scrollbar-none" ref={containerRef}>
            <div className="relative min-w-max flex items-center justify-between gap-16 px-4 py-8">
                {/* SVG Layer */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
                    <defs>
                        <marker id="causality-arrow"
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
                            markerEnd="url(#causality-arrow)"
                        />
                    ))}
                </svg>

                {/* Nodes Layer */}
                {nodes.map((node, i) => (
                    <motion.div
                        key={node.id || i}
                        ref={el => nodeRefs.current[node.id || i] = el}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className="relative z-10 flex flex-col items-center gap-2"
                    >
                        <div className="w-10 h-10 rounded-full bg-neutral-900 border border-neutral-800 flex items-center justify-center text-accent shadow-lg shadow-black/40">
                            {node.type === 'stimulus' ? <Beaker className="w-5 h-5" /> :
                                node.type === 'response' ? <Target className="w-5 h-5" /> :
                                    <Activity className="w-5 h-5" />}
                        </div>
                        <div className="flex flex-col items-center max-w-[100px] text-center">
                            <span className="text-[10px] font-bold text-neutral-200 uppercase tracking-tight truncate w-full">
                                {node.label || node.id}
                            </span>
                            <span className="text-[8px] font-mono text-neutral-500 uppercase tracking-widest">{node.type}</span>
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
});

export default CausalityGraph;

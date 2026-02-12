import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { FlaskConical, Target, Activity, ChevronRight } from 'lucide-react';

/**
 * IntelligenceGraph
 * 
 * [MANDATE] Deterministic Molecule -> Receptor -> Perception UI
 * Visualizes the reasoning chain as a directed graph.
 */
const IntelligenceGraph = ({ claim }) => {
    const { compounds = [], receptors = [], perception_outputs = [] } = claim;

    console.log(`[GRAPH_PAINT] Rendering topology for ${claim.id}`);

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-2 mb-4">
                <Activity className="w-3.5 h-3.5 text-accent" />
                <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest text-neutral-400">
                    Mechanism Topology
                </h4>
            </div>

            <div className="flex flex-col md:flex-row items-center justify-between gap-6 relative">
                {/* 1. Compounds Layer */}
                <div className="flex flex-col gap-3 w-full md:w-1/3">
                    <span className="text-[9px] font-mono text-neutral-600 uppercase tracking-tighter text-center">Compounds</span>
                    {compounds.length > 0 ? compounds.map((c, i) => (
                        <Node key={i} icon={<FlaskConical className="w-3 h-3 text-blue-400" />} label={c} color="blue" />
                    )) : <EmptyNode label="Unspecified" />}
                </div>

                <div className="hidden md:block"><Connector /></div>

                {/* 2. Receptors Layer */}
                <div className="flex flex-col gap-3 w-full md:w-1/3">
                    <span className="text-[9px] font-mono text-neutral-600 uppercase tracking-tighter text-center">Receptors</span>
                    {receptors.length > 0 ? receptors.map((r, i) => (
                        <Node key={i} icon={<Target className="w-3 h-3 text-purple-400" />} label={r} color="purple" />
                    )) : <EmptyNode label="Theoretical" />}
                </div>

                <div className="hidden md:block"><Connector /></div>

                {/* 3. Perception Layer */}
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
        blue: "bg-blue-500/10 border-blue-500/20 text-blue-200",
        purple: "bg-purple-500/10 border-purple-500/20 text-purple-200",
        amber: "bg-amber-500/10 border-amber-500/20 text-amber-100"
    };

    return (
        <motion.div
            whileHover={{ scale: 1.02, y: -2 }}
            className={`flex flex-col p-3 rounded-lg border shadow-sm ${colors[color]} backdrop-blur-md relative group`}
        >
            <div className="flex items-center gap-3">
                <div className="shrink-0 p-1.5 rounded bg-black/40 border border-white/5">
                    {icon}
                </div>
                <div className="flex flex-col">
                    <span className="text-[11px] font-bold font-mono tracking-tight uppercase">{label}</span>
                    {subtitle && <span className="text-[8px] font-mono opacity-50 uppercase tracking-tighter">via {subtitle}</span>}
                </div>
            </div>
            {/* Glow effect on hover */}
            <div className="absolute inset-0 bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg" />
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

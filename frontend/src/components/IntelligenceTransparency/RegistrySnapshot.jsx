import React from 'react';
import { DatabaseZap, Lock, Unlock, Hash, Info, AlertTriangle } from 'lucide-react';

/**
 * RegistrySnapshot
 * 
 * KNOWLEDGE STATE AUDIT TERMINAL:
 * - Displays the exact ontology and registry state used for computation.
 * - Enables computational replay and drift defense.
 * - Fails loudly (visually) if snapshot data is missing.
 */
const RegistrySnapshot = ({ snapshot }) => {
    const isLocked = snapshot?.locked;
    const hasData = (snapshot?.version || snapshot?.registry_version) && (snapshot?.registry_hash || snapshot?.hash);

    if (!snapshot || !hasData) {
        return (
            <div className="p-4 rounded-xl bg-red-500/5 border-2 border-dashed border-red-500/20 flex flex-col items-center gap-2 text-center">
                <AlertTriangle className="w-6 h-6 text-red-500 animate-pulse" />
                <div className="space-y-1">
                    <p className="text-[10px] font-black text-red-500 uppercase tracking-tighter">STATE_INTEGRITY_FAILURE</p>
                    <p className="text-[9px] text-red-400/60 font-mono">Registry snapshot missing or corrupted.</p>
                </div>
            </div>
        );
    }

    const version = snapshot.version || snapshot.registry_version;
    const hash = snapshot.registry_hash || snapshot.hash;

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between px-1">
                <p className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest">Knowledge State (Snapshot)</p>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1.5 px-1.5 py-0.5 rounded bg-neutral-800 border border-neutral-700">
                        <span className="text-[8px] font-mono text-neutral-500 uppercase tracking-tighter">Scope:</span>
                        <span className="text-[8px] font-mono text-neutral-300 uppercase">{snapshot.scope || 'Global'}</span>
                    </div>
                    {isLocked ? (
                        <div className="flex items-center gap-1 text-[8px] font-mono text-green-500 uppercase">
                            <Lock className="w-2.5 h-2.5" />
                            <span>Sealed</span>
                        </div>
                    ) : (
                        <div className="flex items-center gap-1 text-[8px] font-mono text-amber-500 uppercase">
                            <Unlock className="w-2.5 h-2.5" />
                            <span>Not Sealed</span>
                        </div>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-1 gap-2 p-3 rounded-xl bg-black/40 border border-neutral-800">
                <div className="flex items-start gap-3">
                    <DatabaseZap className="w-4 h-4 text-blue-400 mt-1" />
                    <div className="flex-1 space-y-2">
                        <div className="grid grid-cols-2 gap-2">
                            <div className="space-y-0.5">
                                <span className="text-[7px] font-mono text-neutral-600 uppercase">Registry Version</span>
                                <p className="text-[10px] font-mono text-neutral-300">v{version}</p>
                            </div>
                            <div className="space-y-0.5">
                                <span className="text-[7px] font-mono text-neutral-600 uppercase">Ontology Version</span>
                                <p className="text-[10px] font-mono text-neutral-300">v{snapshot.ontology_version}</p>
                            </div>
                        </div>

                        <div className="space-y-1 border-t border-neutral-800/50 pt-2">
                            <div className="flex items-center gap-1.5">
                                <Hash className="w-2.5 h-2.5 text-neutral-600" />
                                <span className="text-[7px] font-mono text-neutral-600 uppercase">Deterministic State Hash</span>
                            </div>
                            <p className="text-[8px] font-mono text-blue-400/50 break-all select-all hover:text-blue-400 transition-colors">
                                {hash}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="mt-2 flex items-center gap-2 px-2 py-1.5 rounded bg-blue-500/5 border border-blue-500/10">
                    <Info className="w-3 h-3 text-blue-400/50" />
                    <p className="text-[8px] text-neutral-500 italic leading-tight">
                        This hash represents the exact configuration of biochemical pathways and molecular indices at T=0.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default RegistrySnapshot;

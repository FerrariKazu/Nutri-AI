import React from 'react';
import { AlertOctagon, ShieldAlert, FileWarning } from 'lucide-react';

/**
 * IntegrityBarrier
 * 
 * LOUD FAILURE TERMINAL:
 * - Dominates the entire panel if a contract violation is detected.
 * - Stops all subordinate rendering.
 * - Categorizes the failure (Policy vs Registry vs Evidence).
 */
const IntegrityBarrier = ({ type, missingFields, context }) => {
    return (
        <div className="absolute inset-0 z-50 flex items-center justify-center p-6 bg-black/95 backdrop-blur-md rounded-xl border-2 border-red-500/50">
            <div className="max-w-md w-full space-y-6 text-center">
                <div className="relative inline-block">
                    <div className="absolute inset-0 animate-ping rounded-full bg-red-500/20" />
                    <div className="relative p-4 rounded-full bg-red-500/10 border border-red-500/30">
                        <AlertOctagon className="w-12 h-12 text-red-500" />
                    </div>
                </div>

                <div className="space-y-2">
                    <h2 className="text-xl font-black text-red-500 uppercase tracking-tighter">
                        Integrity Violation Detected
                    </h2>
                    <p className="text-[10px] font-mono text-red-400/60 uppercase tracking-widest">
                        Contract Barrier: {type} Violation
                    </p>
                </div>

                <div className="p-4 rounded-lg bg-red-500/5 border border-red-500/10 space-y-3">
                    <div className="flex items-center gap-2 justify-center text-red-400">
                        <ShieldAlert className="w-4 h-4" />
                        <span className="text-xs font-bold font-mono">CRITICAL_SCHEMA_GAP</span>
                    </div>

                    <div className="space-y-1">
                        {missingFields?.map((field, i) => (
                            <div key={i} className="text-[10px] font-mono py-1 px-2 rounded bg-red-500/10 text-red-300 border border-red-500/20 inline-block m-0.5">
                                {field}
                            </div>
                        ))}
                    </div>
                </div>

                <div className="text-[9px] font-mono text-neutral-500 leading-relaxed text-left max-w-[280px] mx-auto italic">
                    Rendering aborted to prevent misleading partial judgments. This trace contains unverified or corrupted epistemological mappings.
                    {context && (
                        <div className="mt-2 p-2 rounded bg-neutral-900 border border-neutral-800 text-neutral-400 not-italic">
                            Ctx: {context}
                        </div>
                    )}
                </div>

                <div className="pt-4 flex items-center gap-2 justify-center opacity-30 hover:opacity-100 transition-opacity">
                    <FileWarning className="w-3 h-3 text-neutral-600" />
                    <span className="text-[8px] font-mono text-neutral-600 uppercase tracking-tighter">
                        Institution-Grade Audit Guard active
                    </span>
                </div>
            </div>
        </div>
    );
};

export default IntegrityBarrier;

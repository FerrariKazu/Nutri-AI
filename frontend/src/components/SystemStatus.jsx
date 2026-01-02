import React from 'react';
import { Activity, Database, Zap, ShieldAlert } from 'lucide-react';

/**
 * SystemStatus - Non-intrusive telemetry bar.
 * Communicates system state, session info, and constraints.
 */
const SystemStatus = ({ sessionId, turnCount, confidence = 'High', warnings = [] }) => {
    const shortSessionId = sessionId ? sessionId.split('_').pop()?.substring(0, 8) : '--------';

    return (
        <div className="flex items-center justify-between px-6 py-2 border-b border-neutral-800 bg-neutral-900/80 backdrop-blur-none h-10 select-none">
            <div className="flex items-center gap-6">
                {/* Session Identification */}
                <div className="flex items-center gap-2">
                    <Database className="w-3 h-3 text-neutral-400" />
                    <span className="text-[10px] font-mono uppercase tracking-widest text-neutral-400">
                        Session: <span className="text-neutral-100">{shortSessionId}</span>
                    </span>
                </div>

                {/* Turn Count / Memory Depth */}
                <div className="flex items-center gap-2">
                    <Activity className="w-3 h-3 text-neutral-400" />
                    <span className="text-[10px] font-mono uppercase tracking-widest text-neutral-400">
                        Context: <span className="text-neutral-100">{turnCount} Turns</span>
                    </span>
                </div>
            </div>

            <div className="flex items-center gap-6">
                {/* Confidence Level */}
                <div className="flex items-center gap-2">
                    <Zap className="w-3 h-3 text-accent/70" />
                    <span className="text-[10px] font-mono uppercase tracking-widest text-neutral-400">
                        Confidence: <span className="text-accent">{confidence}</span>
                    </span>
                </div>

                {/* Warnings Indicator */}
                {warnings.length > 0 && (
                    <div className="flex items-center gap-2 px-2 py-0.5 rounded bg-accent-muted/30 border border-accent/20">
                        <ShieldAlert className="w-3 h-3 text-accent" />
                        <span className="text-[10px] font-mono uppercase tracking-widest text-accent">
                            {warnings.length} Conflicts
                        </span>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SystemStatus;

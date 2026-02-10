import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Brain,
    ChevronDown,
    Cpu,
    Copy,
    Check,
    Info,
    Settings2,
    ShieldCheck,
    MessageSquare,
    Share2,
    FileJson,
    Loader2,
    AlertTriangle,
    ZapOff,
    FileSearch,
    DatabaseZap
} from 'lucide-react';
import Tier1Evidence from './Tier1Evidence';
import Tier2Mechanism from './Tier2Mechanism';
import Tier3Causality from './Tier3Causality';
import Tier4Temporal from './Tier4Temporal';
import ConfidenceTracker from './ConfidenceTracker';
import { Tooltip, getConfidenceNarrative } from './UIUtils';
import { renderPermissions } from '../../contracts/renderPermissions';

/**
 * NutriIntelligencePanel
 * 
 * STRICT MODE CONTAINER:
 * - Data Provenance Footer (Mandatory).
 * - Raw Trace JSON View (Expert).
 * - Stream State Awareness (Streaming vs Complete).
 * - Schema Mismatch Handling.
 */
const NutriIntelligencePanel = React.memo(({ uiTrace, expertModeDefault = false }) => {
    useEffect(() => {
        console.log("%c INTELLIGENCE PANEL MOUNTED ", "background: #3b82f6; color: white; font-weight: bold; padding: 2px 4px; border-radius: 4px;");
    }, []);

    const [isOpen, setIsOpen] = useState(false);
    const [isExpertMode, setIsExpertMode] = useState(expertModeDefault);
    const [isRawView, setIsRawView] = useState(false);
    const [selectedClaimIdx, setSelectedClaimIdx] = useState(0);
    const [copied, setCopied] = useState(false);
    const [shared, setShared] = useState(false);

    useEffect(() => {
        const savedMode = localStorage.getItem('nutri_expert_mode');
        if (savedMode !== null) {
            setIsExpertMode(savedMode === 'true');
        }
    }, []);

    const toggleExpertMode = (e) => {
        e.stopPropagation();
        const newMode = !isExpertMode;
        setIsExpertMode(newMode);
        localStorage.setItem('nutri_expert_mode', newMode);
    };

    const toggleRawView = (e) => {
        e.stopPropagation();
        setIsRawView(!isRawView);
    };

    const handleClaimSelect = (idx) => {
        setSelectedClaimIdx(idx);
    };

    // 🚀 Strict Copy: Raw JSON only
    const handleCopy = useCallback(() => {
        const text = JSON.stringify(uiTrace, null, 2);
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    }, [uiTrace]);

    if (!uiTrace) return null;

    // Safety: Ensure selected index is valid
    const currentClaim = uiTrace.claims && uiTrace.claims.length > 0
        ? (uiTrace.claims[selectedClaimIdx] || uiTrace.claims[0])
        : null;

    // Schema/Status Checks
    const isStreaming = uiTrace.status === 'streaming';
    const isComplete = uiTrace.status === 'complete';

    // Integrity Message - NO FLUFF
    const integrityMessage = useMemo(() => {
        if (uiTrace.metrics.pubchemUsed) return "Verified via PubChem P0 Protocol";
        if (uiTrace.claims.length === 0) return "Descriptive Response Evaluation";
        return "Synthesized from Knowledge Graph";
    }, [uiTrace]);

    // Detection Rule for Semantic 'No Verification Required'
    const isNoClaimsDescriptive = useMemo(() => {
        return uiTrace.claims.length === 0 &&
            (uiTrace.warnings || []).includes("No claims found in trace");
    }, [uiTrace]);


    return (
        <div className="mt-6 border border-neutral-800 rounded-xl overflow-hidden bg-neutral-900/20 backdrop-blur-sm animate-fade-in shadow-2xl text-card-foreground">
            {/* 🛡️ Status & Integrity Banner */}
            <div className={`px-4 py-1.5 border-b border-neutral-800/50 flex items-center gap-2 overflow-hidden ${isStreaming ? 'bg-blue-500/5' : 'bg-neutral-900/40'}`}>
                {isStreaming ? (
                    <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />
                ) : (
                    <ShieldCheck className="w-3 h-3 text-neutral-500" />
                )}

                <p className="text-[10px] font-mono uppercase tracking-tight text-neutral-400 truncate flex-1">
                    {isStreaming ? "Reasoning Stream Active..." : integrityMessage}
                </p>

                <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 rounded-full text-[8px] font-bold font-mono border ${isStreaming ? 'text-blue-400 border-blue-500/20 bg-blue-500/10' : 'text-neutral-500 border-neutral-700/50 bg-neutral-800'
                        }`}>
                        {uiTrace.status ? uiTrace.status.toUpperCase() : 'UNKNOWN'}
                    </span>
                </div>
            </div>

            {/* Header / Trigger */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between p-4 hover:bg-neutral-800/30 transition-all duration-300 group"
            >
                <div className="flex items-center gap-3 text-left">
                    <div className="p-2 rounded-lg bg-accent/10 text-accent group-hover:scale-110 group-hover:bg-accent/20 transition-all duration-500">
                        <Brain className="w-4 h-4" />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h3 className="text-xs font-bold uppercase tracking-[0.15em] text-neutral-200 group-hover:text-white transition-colors">
                                Nutri Intelligence Panel v2.1
                            </h3>
                        </div>
                        <p className="text-[10px] text-neutral-500 font-mono mt-0.5">
                            {uiTrace.claims.length} Verified Claims • {uiTrace.metrics.duration}ms Latency
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-[10px] font-mono text-neutral-600 group-hover:text-neutral-400 transition-colors uppercase">
                        {isOpen ? 'Close' : 'Inspect'}
                    </span>
                    <div className={`transition-transform duration-500 ${isOpen ? 'rotate-180' : ''}`}>
                        <ChevronDown className="w-4 h-4 text-neutral-600" />
                    </div>
                </div>
            </button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.3 }}
                        className="overflow-hidden border-t border-neutral-800"
                    >
                        {/* Control Bar */}
                        <div className="px-4 py-3 bg-neutral-950/60 border-b border-neutral-800 flex items-center justify-between text-[11px]">
                            <div className="flex items-center gap-2 text-neutral-400">
                                <Info className="w-3.5 h-3.5 text-neutral-600" />
                                <span>System Execution Telemetry</span>
                            </div>

                            <div className="flex items-center gap-4">
                                {/* Raw Toggle */}
                                <button
                                    onClick={toggleRawView}
                                    className={`flex items-center gap-1.5 transition-colors group ${isRawView ? 'text-accent' : 'text-neutral-500 hover:text-neutral-300'}`}
                                >
                                    <FileJson className="w-3 h-3" />
                                    <span className="font-mono uppercase tracking-tighter">Raw JSON</span>
                                </button>

                                {/* Expert Toggle */}
                                <button
                                    onClick={toggleExpertMode}
                                    className={`flex items-center gap-1.5 transition-all group ${isExpertMode ? 'text-accent' : 'text-neutral-500 hover:text-neutral-300'}`}
                                >
                                    <Settings2 className={`w-3 h-3 ${isExpertMode ? 'rotate-180' : ''} transition-transform`} />
                                    <span className="font-mono uppercase tracking-tighter">Expert</span>
                                </button>
                            </div>
                        </div>

                        {/* Raw View Mode */}
                        {isRawView ? (
                            <div className="p-4 bg-neutral-950 font-mono text-[10px] text-green-400 overflow-auto max-h-[500px]">
                                <pre>{JSON.stringify(uiTrace, null, 2)}</pre>
                            </div>
                        ) : (
                            <>
                                {/* Claim Selector */}
                                {uiTrace.claims.length > 1 && (
                                    <div className="px-4 py-2 flex items-center gap-2 border-b border-neutral-800 bg-neutral-900/10 overflow-x-auto scrollbar-none">
                                        <MessageSquare className="w-3 h-3 text-neutral-700 shrink-0 mr-1" />
                                        {uiTrace.claims.map((claim, idx) => (
                                            <button
                                                key={claim.id || idx}
                                                onClick={() => handleClaimSelect(idx)}
                                                className={`shrink-0 px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all duration-300 ${selectedClaimIdx === idx
                                                    ? 'bg-neutral-200 text-neutral-950'
                                                    : 'text-neutral-500 hover:text-neutral-300 bg-neutral-800/40'
                                                    }`}
                                            >
                                                CLAIM {idx + 1}
                                            </button>
                                        ))}
                                    </div>
                                )}

                                {/* Main Grid */}
                                <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-10 bg-neutral-900/40">
                                    {currentClaim ? (
                                        <>
                                            {/* ... existing tiers rendering ... */}
                                            {/* (Note: Truncated for diff simplicity, keeping original logic) */}
                                            <div className="space-y-10">
                                                <section>
                                                    <Tier1Evidence
                                                        trace={uiTrace}
                                                        claim={currentClaim}
                                                        metrics={uiTrace.metrics}
                                                        expertMode={isExpertMode}
                                                    />
                                                </section>

                                                {renderPermissions.canRenderTier2({ claims: [currentClaim] }).allowed && (
                                                    <section className="pt-10 border-t border-neutral-800/50">
                                                        <Tier2Mechanism
                                                            trace={uiTrace}
                                                            claim={currentClaim}
                                                            expertMode={isExpertMode}
                                                        />
                                                    </section>
                                                )}
                                            </div>

                                            <div className="space-y-10">
                                                <section>
                                                    <Tier3Causality
                                                        uiTrace={uiTrace}
                                                        claimIdx={selectedClaimIdx}
                                                        expertMode={isExpertMode}
                                                    />
                                                </section>

                                                {renderPermissions.canRenderTier4(uiTrace).allowed && (
                                                    <section className="pt-10 border-t border-neutral-800/50">
                                                        <Tier4Temporal
                                                            uiTrace={uiTrace}
                                                            claimIdx={selectedClaimIdx}
                                                            expertMode={isExpertMode}
                                                        />
                                                    </section>
                                                )}

                                                <section className="pt-10 border-t border-neutral-800/50">
                                                    <ConfidenceTracker
                                                        uiTrace={uiTrace}
                                                        claimIdx={selectedClaimIdx}
                                                        expertMode={isExpertMode}
                                                    />
                                                </section>
                                            </div>
                                        </>
                                    ) : isNoClaimsDescriptive ? (
                                        <div className="col-span-full py-16 flex flex-col items-center text-center animate-in fade-in slide-in-from-bottom-2 duration-700">
                                            <div className="p-4 rounded-full bg-blue-500/10 border border-blue-500/20 mb-6">
                                                <Info className="w-8 h-8 text-blue-400/80" />
                                            </div>

                                            <h4 className="text-lg font-bold text-neutral-100 mb-2">
                                                No verification required
                                            </h4>

                                            <p className="text-xs text-neutral-400 max-w-md leading-relaxed mb-10">
                                                The assistant response contains descriptive or experiential information.
                                                It does not introduce biochemical, medical, or nutritional claims
                                                that require evidence validation.
                                            </p>

                                            <div className="flex flex-wrap justify-center gap-3">
                                                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-neutral-800/50 border border-neutral-700/30 text-[10px] font-mono text-neutral-400">
                                                    <Brain className="w-3 h-3 text-accent/60" />
                                                    DIRECT SYNTHESIS
                                                </div>
                                                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-neutral-800/50 border border-neutral-700/30 text-[10px] font-mono text-neutral-400">
                                                    <ZapOff className="w-3 h-3 text-yellow-500/60" />
                                                    NO EXTERNAL DATA
                                                </div>
                                                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-neutral-800/50 border border-neutral-700/30 text-[10px] font-mono text-neutral-400">
                                                    <ShieldCheck className="w-3 h-3 text-green-500/60" />
                                                    NO RISK ANALYSIS TRIGGERED
                                                </div>
                                            </div>

                                            {/* Execution Telemetry Summary (for non-expert view) */}
                                            {!isExpertMode && (
                                                <div className="mt-12 pt-8 border-t border-neutral-800/50 w-full max-w-xs flex justify-around opacity-40 grayscale">
                                                    <div className="flex flex-col items-center gap-1">
                                                        <div className="w-1 h-1 rounded-full bg-blue-500 opacity-50" />
                                                        <span className="text-[8px] font-mono uppercase tracking-tighter">Streaming Status</span>
                                                    </div>
                                                    <div className="flex flex-col items-center gap-1">
                                                        <div className="w-1 h-1 rounded-full bg-green-500 opacity-50" />
                                                        <span className="text-[8px] font-mono uppercase tracking-tighter">Validation Stage</span>
                                                    </div>
                                                    <div className="flex flex-col items-center gap-1">
                                                        <div className="w-1 h-1 rounded-full bg-accent opacity-50" />
                                                        <span className="text-[8px] font-mono uppercase tracking-tighter">Trace Available</span>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <div className="col-span-full py-20 flex flex-col items-center justify-center gap-4 text-neutral-500">
                                            <Info className="w-8 h-8 opacity-20" />
                                            <p className="text-xs font-mono uppercase tracking-widest text-center max-w-xs leading-relaxed">
                                                No structured claims were produced for this response.
                                                <br />
                                                <span className="opacity-50 mt-2 block">(All tokens were direct synthesis)</span>
                                            </p>
                                        </div>
                                    )}
                                </div>
                            </>
                        )}

                        {/* 🦶 Data Provenance Footer (MANDATORY) */}
                        <div className="px-5 py-3 border-t border-neutral-800 bg-neutral-950 flex items-center justify-between">
                            <div className="flex items-center gap-2 opacity-50">
                                <ShieldCheck className="w-3 h-3 text-neutral-500" />
                                <span className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest">
                                    Generated from runtime execution trace. Only verified system outputs displayed.
                                </span>
                            </div>
                            <span className="text-[9px] font-mono text-neutral-700">
                                Schema v{uiTrace.schema_version || '1.0'}
                            </span>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
});

export default NutriIntelligencePanel;

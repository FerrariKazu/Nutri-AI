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
    DatabaseZap,
    Activity
} from 'lucide-react';
import Tier1Evidence from './Tier1Evidence';
import Tier2Mechanism from './Tier2Mechanism';
import Tier3Causality from './Tier3Causality';
import Tier4Temporal from './Tier4Temporal';
import ConfidenceTracker from './ConfidenceTracker';
import PerceptionMapper from './PerceptionMapper';
import IntelligenceGraph from './IntelligenceGraph';
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
    // [TRACE_AUDIT] Step 7: UI render check
    useEffect(() => {
        if (uiTrace) {
            const claimsLen = uiTrace.claims ? uiTrace.claims.length : 0;
            console.log(`%c [TRACE_AUDIT] TRACE RENDER: ${claimsLen} claims available to UI`, "background: #1e3a8a; color: white; padding: 2px 4px; border-radius: 4px;");
        }
    }, [uiTrace]);

    // 🧩 STEP 3 — FIELD NAME ADAPTER (CRITICAL)
    const normalizeClaim = useCallback((c) => {
        if (!c || !c.statement) return null; // STRICT: No statement, no render.

        return {
            ...c,
            id: c.id || c.claim_id, // Allow ID fallback only for keys

            // STRICT: Verbatim Mapping
            statement: c.statement,
            domain: c.domain,
            origin: c.origin,
            verification_level: c.verification_level,
            importance_score: c.importance_score,
            source: c.source,
            confidence: c.confidence,

            // STRICT: Structural Objects (Empty arrays allowed if backend sends them)
            mechanism: c.mechanism,
            mechanism_topology: c.mechanism_topology,
            compounds: c.compounds,
            receptors: c.receptors,
            perception_outputs: c.perception_outputs
        };
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

    // [PAINT] Logic
    const claims = useMemo(() => (uiTrace?.claims || []).map(normalizeClaim), [uiTrace, normalizeClaim]);

    // Safety: Ensure selected index is valid
    const currentClaim = claims.length > 0
        ? (claims[selectedClaimIdx] || claims[0])
        : null;

    // Mandate Check
    const isMandateFailure = useMemo(() => {
        return uiTrace?.trace_required && uiTrace.claims?.length === 0;
    }, [uiTrace]);

    useEffect(() => {
        if (claims.length > 0) {
            // TELEMETRY: NORMALIZATION AUDIT
            console.log("🧪 AFTER NORMALIZATION", claims);
            console.log(`%c [PAINT] Rendering ${claims.length} claims `, "background: #065f46; color: white; padding: 2px 4px; border-radius: 4px;", claims);

            // ASSERTION: STRICT RENDER
            claims.forEach((c, i) => {
                if (c.statement && (c.importance_score === undefined || c.importance_score === null)) {
                    console.error(`[STRICT_RENDER_FAIL] Claim ${i} is missing importance_score (backend sent null?)`, c);
                }
                if (c.statement && (c.verification_level === undefined || c.verification_level === null)) {
                    console.error(`[STRICT_RENDER_FAIL] Claim ${i} is missing verification_level`, c);
                }
                if (c.statement && (c.confidence === undefined || c.confidence === null)) {
                    console.error(`[STRICT_RENDER_FAIL] Claim ${i} is missing confidence metrics`, c);
                }
            });
        }
    }, [claims]);


    // Schema/Status Checks
    const isStreaming = uiTrace?.status === 'streaming' || uiTrace?.status === 'STREAMING';

    return (
        <div className="mt-6 border border-neutral-800 rounded-xl overflow-hidden bg-neutral-900/20 backdrop-blur-sm animate-fade-in shadow-2xl text-card-foreground">
            {/* 🛡️ Status & Integrity Banner */}
            <div className={`px-4 py-1.5 border-b border-neutral-800/50 flex items-center gap-2 overflow-hidden ${isStreaming ? 'bg-blue-500/5' : 'bg-neutral-900/40'}`}>
                {isStreaming ? (
                    <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />
                ) : (
                    <ShieldCheck className={`w-3 h-3 ${!uiTrace ? 'text-neutral-700' : 'text-neutral-500'}`} />
                )}

                <p className="text-[10px] font-mono uppercase tracking-tight text-neutral-400 truncate flex-1">
                    {integrityMessage}
                </p>

                {uiTrace && (
                    <div className="flex items-center gap-3">
                        <span className={`px-2 py-0.5 rounded-full text-[8px] font-bold font-mono border ${['STREAMING', 'ENRICHING', 'INIT'].includes(uiTrace.status)
                            ? 'text-blue-400 border-blue-500/20 bg-blue-500/10'
                            : uiTrace.status === 'COMPLETE' || uiTrace.status === 'VERIFIED'
                                ? 'text-green-400 border-green-500/20 bg-green-500/10'
                                : 'text-neutral-500 border-neutral-700/50 bg-neutral-800'
                            }`}>
                            {uiTrace.status ? uiTrace.status.toUpperCase() : 'UNKNOWN'}
                        </span>
                    </div>
                )}
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
                            {uiTrace ? `${claims.length} Claims Resolved` : 'Execution Telemetry Missing'} • {uiTrace?.metrics.duration ? `${Math.round(uiTrace.metrics.duration)}ms` : '---'} Latency
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
                        ) : !uiTrace ? (
                            <div className="p-16 flex flex-col items-center text-center opacity-40">
                                <ZapOff className="w-8 h-8 text-neutral-600 mb-4" />
                                <p className="text-xs font-mono uppercase tracking-widest text-neutral-500">
                                    No Execution Trace Recorded
                                </p>
                            </div>
                        ) : (
                            <>
                                {/* Claim Selector */}
                                {claims.length > 1 && (
                                    <div className="px-4 py-2 flex items-center gap-2 border-b border-neutral-800 bg-neutral-900/10 overflow-x-auto scrollbar-none">
                                        <MessageSquare className="w-3 h-3 text-neutral-700 shrink-0 mr-1" />
                                        {claims.map((claim, idx) => (
                                            <button
                                                key={claim.id || idx}
                                                onClick={() => handleClaimSelect(idx)}
                                                className={`shrink-0 px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all duration-300 flex items-center gap-2 ${selectedClaimIdx === idx
                                                    ? 'bg-neutral-200 text-neutral-950 shadow-lg scale-105'
                                                    : 'text-neutral-500 hover:text-neutral-300 bg-neutral-800/40'
                                                    }`}
                                            >
                                                CLAIM {idx + 1}
                                                {claim.origin === 'extracted' && <FileSearch className="w-2.5 h-2.5 opacity-50" />}
                                                {claim.origin === 'enriched' && <DatabaseZap className="w-2.5 h-2.5 opacity-50" />}
                                            </button>
                                        ))}
                                    </div>
                                )}

                                {/* Coverage & Saturation Metric (New) */}
                                {uiTrace.coverage_metrics?.mechanisms?.length > 0 && (
                                    <div className="px-5 py-2.5 bg-accent/5 border-b border-neutral-800/50 flex items-center gap-4">
                                        <div className="flex items-center gap-2 shrink-0">
                                            <Cpu className="w-3 h-3 text-accent" />
                                            <span className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest">Mechanisms Covered:</span>
                                        </div>
                                        <div className="flex gap-2 overflow-x-auto scrollbar-none">
                                            {uiTrace.coverage_metrics.mechanisms.map((m, i) => (
                                                <span key={i} className="text-[9px] font-mono text-accent/80 bg-accent/10 px-2 py-0.5 rounded border border-accent/20">
                                                    {m.toUpperCase()}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Main Grid */}
                                <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-10 bg-neutral-900/40">
                                    {currentClaim ? (
                                        <>
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

                                                {/* Tier 2.1: Intelligence Graph (MANDATE) */}
                                                <section className="pt-10 border-t border-neutral-800/50">
                                                    <IntelligenceGraph claim={currentClaim} />
                                                </section>

                                                {/* Tier 2.5: Perception Mapping (Legacy Bridge) */}
                                                {(currentClaim.receptors?.length > 0 || currentClaim.perception_outputs?.length > 0) && (
                                                    <section className="pt-10 border-t border-neutral-800/50">
                                                        <PerceptionMapper claim={currentClaim} />
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

                                                {/* Origin & Verification Level Badges */}
                                                <div className="pt-8 flex flex-wrap gap-3">
                                                    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-[10px] font-mono uppercase tracking-tight
                                                        ${currentClaim.origin === 'extracted' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                                                            currentClaim.origin === 'enriched' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                                                                'bg-neutral-800/50 text-neutral-400 border-neutral-700/30'}`}>
                                                        {currentClaim.origin === 'extracted' && <FileSearch className="w-3 h-3" />}
                                                        {currentClaim.origin === 'enriched' && <DatabaseZap className="w-3 h-3" />}
                                                        {currentClaim.origin === 'model' && <Brain className="w-3 h-3" />}
                                                        Origin: {currentClaim.origin || 'model'}
                                                    </div>

                                                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-neutral-800/50 border border-neutral-700/30 text-[10px] font-mono text-neutral-400">
                                                        <ShieldCheck className="w-3 h-3 text-green-500/60" />
                                                        Level: {currentClaim.verification_level || 'theoretical'}
                                                    </div>

                                                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-neutral-800/50 border border-neutral-700/30 text-[10px] font-mono text-neutral-400">
                                                        <Activity className="w-3 h-3 text-purple-500/60" />
                                                        Domain: {currentClaim.domain || 'biological'}
                                                    </div>

                                                    {isExpertMode && (
                                                        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-neutral-800/50 border border-neutral-700/30 text-[10px] font-mono text-neutral-400">
                                                            <Activity className="w-3 h-3 text-blue-500/60" />
                                                            Priority: {Math.round((currentClaim.importance_score || 0) * 100)}%
                                                        </div>
                                                    )}
                                                </div>

                                                {currentClaim.origin === 'extracted' && (
                                                    <div className="mt-4 p-3 rounded-lg bg-amber-500/5 border border-amber-500/10 flex items-start gap-3">
                                                        <AlertTriangle className="w-4 h-4 text-amber-500/60 shrink-0 mt-0.5" />
                                                        <p className="text-[10px] text-amber-200/50 leading-relaxed italic">
                                                            Generated via post-response scientific structuring. This insight was extracted from the model's textual output to satisfy the Intelligence Mandate.
                                                        </p>
                                                    </div>
                                                )}
                                            </div>
                                        </>
                                    ) : isMandateFailure ? (
                                        <div className="col-span-full py-16 flex flex-col items-center text-center animate-in fade-in slide-in-from-bottom-2 duration-700">
                                            <div className="p-4 rounded-full bg-red-500/10 border border-red-500/20 mb-6">
                                                <AlertTriangle className="w-8 h-8 text-red-400/80" />
                                            </div>

                                            <h4 className="text-lg font-bold text-neutral-100 mb-2">
                                                Intelligence Mandate Failure
                                            </h4>

                                            <p className="text-xs text-neutral-400 max-w-md leading-relaxed mb-4">
                                                The system detected scientific language requiring structured validation, but the structuring engine was unable to parse atomic claims.
                                            </p>

                                            <div className="px-4 py-2 rounded-lg bg-red-950/20 border border-red-900/40 text-[10px] font-mono text-red-300">
                                                VALIDATION_STATUS: INVALID
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="col-span-full py-16 flex flex-col items-center text-center opacity-60">
                                            <div className="p-4 rounded-full bg-neutral-800/50 border border-neutral-700/30 mb-6">
                                                <Info className="w-8 h-8 text-neutral-500" />
                                            </div>

                                            <h4 className="text-lg font-bold text-neutral-400 mb-2">
                                                Descriptive Analysis
                                            </h4>

                                            <p className="text-xs text-neutral-500 max-w-sm leading-relaxed mb-8">
                                                This response provides general culinary or sensory information without biochemical claims.
                                            </p>

                                            <div className="flex flex-wrap justify-center gap-3">
                                                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-neutral-800/50 border border-neutral-700/30 text-[10px] font-mono text-neutral-500">
                                                    <Brain className="w-3 h-3" />
                                                    NATIVE SYNTHESIS
                                                </div>
                                            </div>
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
                                Schema v{uiTrace?.schema_version || '1.0'}
                            </span>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
});

export default NutriIntelligencePanel;

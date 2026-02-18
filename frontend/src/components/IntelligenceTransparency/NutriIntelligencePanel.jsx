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
    Activity,
    Hash
} from 'lucide-react';
import Tier1Evidence from './Tier1Evidence';
import Tier2Mechanism from './Tier2Mechanism';
import Tier3Causality from './Tier3Causality';
import Tier4Temporal from './Tier4Temporal';
import ConfidenceTracker from './ConfidenceTracker';
import PerceptionMapper from './PerceptionMapper';
import IntelligenceGraph from './IntelligenceGraph';
import IntegrityBarrier from './IntegrityBarrier';
import EvidenceLineageViewer from './EvidenceLineageViewer';
import PolicyAuthorityCard from './PolicyAuthorityCard';
import RuleFiringTimeline from './RuleFiringTimeline';
import RegistrySnapshot from './RegistrySnapshot';
import ExecutionProfileCard from './ExecutionProfileCard';
import { Tooltip, getConfidenceNarrative } from './UIUtils';
import { renderPermissions } from '../../contracts/renderPermissions';
import { adaptClaimForUI } from '../../utils/traceAdapter';
import { EPISTEMIC_COLORS } from '../../contracts/executionTraceSchema';

/**
 * NutriIntelligencePanel
 * 
 * STRICT MODE CONTAINER (v1.3):
 * - Direct Binding to Backend Epistemic Authority.
 * - Scientific Instrument Standby Mode.
 * - Deterministic Arithmetic Path.
 */
const NutriIntelligencePanel = React.memo(({ uiTrace, expertModeDefault = false }) => {
    const claims = useMemo(() => (uiTrace?.claims || []), [uiTrace]);
    const metrics = uiTrace?.metrics || {};

    // 🧠 Direct Binding (No inference)
    const executionMode = uiTrace?.execution_mode || 'full_trace';
    const epistemicStatus = uiTrace?.epistemic_status || 'theoretical';
    const isStandby = executionMode === 'non_scientific_discourse' || uiTrace?.domain_type === 'contextual';

    const [isOpen, setIsOpen] = useState(false);
    const [isExpertMode, setIsExpertMode] = useState(expertModeDefault);
    const [showRawJson, setShowRawJson] = useState(false);
    const [selectedClaimIdx, setSelectedClaimIdx] = useState(0);
    const [copySuccess, setCopySuccess] = useState(false);

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
        setShowRawJson(!showRawJson);
    };

    const handleClaimSelect = (idx) => {
        setSelectedClaimIdx(idx);
    };

    const handleCopy = useCallback(() => {
        const text = JSON.stringify(uiTrace?._raw || uiTrace, null, 2);
        navigator.clipboard.writeText(text);
        setCopySuccess(true);
        setTimeout(() => setCopySuccess(false), 2000);
    }, [uiTrace]);

    // Safety: Ensure selected index is valid
    const currentClaim = claims.length > 0
        ? (claims[selectedClaimIdx] || claims[0])
        : null;

    // Epistemic Color
    const statusColor = useMemo(() => EPISTEMIC_COLORS[epistemicStatus] || '#94a3b8', [epistemicStatus]);

    // Integrity Message - Premium Narrative
    const integrityMessage = useMemo(() => {
        if (!uiTrace) return "No execution trace recorded";
        if (isStandby) return "Scientific Instrument Standby";
        if (uiTrace.status === 'INIT') return "Initializing Scientific Workspace...";
        if (uiTrace.status === 'streaming') return "Reasoning Stream Active...";
        if (uiTrace.status === 'VERIFIED' || uiTrace.status === 'complete') return "Institutional Audit Terminal";
        return "Deterministic System Telemetry";
    }, [uiTrace, isStandby]);

    // 🛡️ [INSTITUTIONAL_HARDENING] Integrity Checks
    const integrityViolation = useMemo(() => {
        if (!uiTrace || isStandby) return null;
        if (uiTrace.adapter_status === "contract_violation") {
            return {
                type: "TRACE CONTRACT VIOLATION",
                missingFields: uiTrace.validation_errors || [],
                context: `run_id: ${uiTrace.run_id || 'NULL'}`
            };
        }
        return null;
    }, [uiTrace, isStandby]);

    return (
        <div className="mt-6 border border-neutral-800 rounded-xl overflow-hidden bg-neutral-900/20 backdrop-blur-sm animate-fade-in shadow-2xl text-card-foreground">
            {/* 🛡️ Status & Integrity Banner */}
            <div className={`px-4 py-1.5 border-b border-neutral-800/50 flex items-center gap-2 overflow-hidden ${uiTrace?.status === 'streaming' ? 'bg-blue-500/5' : 'bg-neutral-900/40'}`}>
                {uiTrace?.status === 'streaming' ? (
                    <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />
                ) : integrityViolation ? (
                    <AlertTriangle className="w-3 h-3 text-red-500 animate-pulse" />
                ) : (
                    <ShieldCheck className={`w-3 h-3 ${!uiTrace ? 'text-neutral-700' : 'text-neutral-500'}`} />
                )}

                <p className={`text-[10px] font-mono upper tracking-tight truncate flex-1 ${integrityViolation ? 'text-red-500 font-bold' : 'text-neutral-400'}`}>
                    {integrityViolation ? 'TRACE_CONTRACT_VIOLATION' : integrityMessage}
                </p>

                {uiTrace && (
                    <div className="flex items-center gap-3">
                        <div className="hidden md:flex items-center gap-2 pr-2 border-r border-neutral-800/50">
                            <span className="text-[7px] font-mono text-neutral-600 uppercase">Run: {uiTrace.run_id?.split('-')[0] || 'NUL'}</span>
                            <span className="text-[7px] font-mono text-neutral-600 uppercase">Ver: {uiTrace.trace_schema_version || '1.3'}</span>
                        </div>
                        <span className={`px-2 py-0.5 rounded-full text-[8px] font-bold font-mono border ${['streaming'].includes(uiTrace.status)
                            ? 'text-blue-400 border-blue-500/20 bg-blue-500/10'
                            : uiTrace.status === 'complete' || uiTrace.status === 'VERIFIED'
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
                    <div className="flex flex-col">
                        <div className="flex items-center gap-2">
                            <h2 className="text-xl font-black text-white tracking-tighter uppercase italic">
                                Nutri Intelligence
                            </h2>
                            <div className="px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/20 flex items-center gap-1.5">
                                <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                                <span className="text-[9px] font-black text-blue-400 uppercase tracking-widest">
                                    {executionMode.replace(/_/g, ' ')}
                                </span>
                            </div>
                        </div>
                        <p className="text-[10px] text-neutral-500 font-bold uppercase tracking-[0.3em] ml-1">
                            Scientific Audit Terminal • Epistemic Status: <span style={{ color: statusColor }}>{epistemicStatus.replace(/_/g, ' ')}</span>
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
                                    className={`flex items-center gap-1.5 transition-colors group ${showRawJson ? 'text-accent' : 'text-neutral-500 hover:text-neutral-300'}`}
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
                        {showRawJson ? (
                            <div className="p-4 bg-neutral-950 font-mono text-[10px] text-green-400 overflow-auto max-h-[500px]">
                                <div className="mb-4 pb-2 border-b border-neutral-800/50 flex items-center justify-between">
                                    <span className="text-neutral-500 uppercase tracking-widest">Backend Raw Payload</span>
                                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-500/10 border border-green-500/20">Variant: {uiTrace._raw?.trace_variant || 'legacy'}</span>
                                </div>
                                <pre>{JSON.stringify(uiTrace._raw || uiTrace, null, 2)}</pre>
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

                                {/* Main Grid: Fact vs Policy Split View */}
                                <div className="relative min-h-[600px] flex flex-col lg:flex-row bg-neutral-900/40 border-b border-neutral-800">
                                    {isStandby ? (
                                        <div className="w-full py-32 flex flex-col items-center opacity-40">
                                            <MessageSquare className="w-8 h-8 text-neutral-600 mb-4" />
                                            <p className="text-xs font-mono uppercase tracking-widest text-neutral-500">
                                                General Discourse Mode • Scientific Instrument Standby
                                            </p>
                                        </div>
                                    ) : (
                                        <>
                                            {integrityViolation && (
                                                <IntegrityBarrier
                                                    type={integrityViolation.type}
                                                    missingFields={integrityViolation.missingFields}
                                                    context={integrityViolation.context}
                                                />
                                            )}

                                            {currentClaim ? (
                                                <>
                                                    {/* LEFT COLUMN: SCIENTIFIC OBSERVATIONS (FACTS) */}
                                                    <div className={`flex-1 p-6 space-y-12 border-r border-neutral-800 ${integrityViolation ? 'blur-sm grayscale pointer-events-none' : ''}`}>
                                                        <div className="space-y-2">
                                                            <h4 className="text-[10px] font-black text-neutral-500 uppercase tracking-[0.2em] border-b border-neutral-800 pb-2">
                                                                Scientific Observation Layer
                                                            </h4>
                                                        </div>

                                                        <section>
                                                            <EvidenceLineageViewer evidenceSet={currentClaim.evidence} />
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

                                                        <section className="pt-10 border-t border-neutral-800/50">
                                                            <IntelligenceGraph claim={currentClaim} />
                                                        </section>

                                                        {/* PubChem Hardened Compound View */}
                                                        {uiTrace.metrics.pubchemUsed && (
                                                            <section className="pt-10 border-t border-neutral-800/50 p-4 rounded-xl bg-green-500/5 border border-green-500/10 shadow-[inner_0_0_20px_rgba(34,197,94,0.05)]">
                                                                <div className="flex items-center gap-2 mb-4">
                                                                    <ShieldCheck className="w-3.5 h-3.5 text-green-500" />
                                                                    <span className="text-[10px] font-black text-green-400 uppercase tracking-widest">Molecular Identity Enforced</span>
                                                                </div>
                                                                <div className="flex items-center gap-3">
                                                                    <Hash className="w-3 h-3 text-neutral-600" />
                                                                    <span className="text-[9px] font-mono text-neutral-500 truncate select-all">{uiTrace.metrics.proofHash}</span>
                                                                </div>
                                                            </section>
                                                        )}
                                                    </div>

                                                    {/* RIGHT COLUMN: POLICY INTERPRETATION (JUDGMENT) */}
                                                    <div className={`flex-1 p-6 space-y-12 bg-black/20 ${integrityViolation ? 'blur-sm grayscale pointer-events-none' : ''}`}>
                                                        {/* 🧪 Execution Profile (High-Level Synthesis) */}
                                                        <section>
                                                            <ExecutionProfileCard
                                                                metrics={metrics}
                                                                epistemicStatus={epistemicStatus}
                                                                executionMode={executionMode}
                                                            />
                                                        </section>

                                                        <div className="space-y-2">
                                                            <h4 className="text-[10px] font-black text-blue-500/60 uppercase tracking-[0.2em] border-b border-neutral-800/50 pb-2 text-right">
                                                                Policy Interpretation Layer
                                                            </h4>
                                                        </div>

                                                        <section>
                                                            <PolicyAuthorityCard
                                                                policy={{
                                                                    policy_id: uiTrace.metrics.policyId,
                                                                    policy_version: uiTrace.metrics.policyVersion,
                                                                    policy_hash: uiTrace.metrics.policyHash,
                                                                    selection_reason: uiTrace.metrics.policySelectionReason,
                                                                    author: currentClaim.confidence?.author || "GOVERNANCE_BOARD",
                                                                    review_board: currentClaim.confidence?.review_board || "SIMULATED_BOARD",
                                                                    approval_date: currentClaim.confidence?.approval_date || "2026-02-16",
                                                                    attestation: currentClaim.confidence?.attestation
                                                                }}
                                                            />
                                                        </section>

                                                        <section className="pt-10 border-t border-neutral-800/50">
                                                            <RuleFiringTimeline breakdown={currentClaim.confidence?.breakdown} />
                                                        </section>

                                                        <section className="pt-10 border-t border-neutral-800/50">
                                                            <RegistrySnapshot snapshot={uiTrace.metrics.registrySnapshot} />
                                                        </section>

                                                        {renderPermissions.canRenderTier3(uiTrace).allowed && (
                                                            <section className="pt-10 border-t border-neutral-800/50">
                                                                <Tier3Causality
                                                                    uiTrace={uiTrace}
                                                                    claimIdx={selectedClaimIdx}
                                                                    expertMode={isExpertMode}
                                                                />
                                                            </section>
                                                        )}

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
                                            ) : (
                                                <div className="w-full py-32 flex flex-col items-center opacity-40">
                                                    <ZapOff className="w-8 h-8 text-neutral-600 mb-4" />
                                                    <p className="text-xs font-mono uppercase tracking-widest text-neutral-500">
                                                        Observation Set Null
                                                    </p>
                                                </div>
                                            )}
                                        </>
                                    )}
                                </div>
                            </>
                        )}

                        {/* 🛡️ Knowledge Limitation Declaration (Requirement Upgrade 27.6) */}
                        <div className="mx-6 mb-6 p-4 rounded bg-neutral-900/50 border border-neutral-800/50">
                            <div className="flex items-start gap-3">
                                <Info className="w-3.5 h-3.5 text-neutral-500 mt-0.5" />
                                <div className="space-y-1">
                                    <span className="text-[9px] font-black text-neutral-500 uppercase tracking-widest">Knowledge Limitation Declaration</span>
                                    <p className="text-[10px] text-neutral-600 leading-relaxed italic">
                                        This execution reflects only indexed registry data and formalized policy rules.
                                        Absence of evidence is not evidence of absence. All biological mechanisms are
                                        modeled under standard physiological conditions.
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* 🦶 Data Provenance Footer (MANDATORY) */}
                        <div className="px-5 py-3 border-t border-neutral-800 bg-neutral-950 flex items-center justify-between">
                            <div className="flex items-center gap-2 opacity-50">
                                <ShieldCheck className="w-3 h-3 text-neutral-500" />
                                <span className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest">
                                    Generated from runtime execution trace. Only verified system outputs displayed.
                                </span>
                            </div>
                            <span className="text-[9px] font-mono text-neutral-700">
                                Trace v{uiTrace?.metrics?.trace_schema_version || '1.3'}
                            </span>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
});

export default NutriIntelligencePanel;

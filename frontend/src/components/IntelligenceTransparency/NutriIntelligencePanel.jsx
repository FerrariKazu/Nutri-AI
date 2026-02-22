import React, { useState, useEffect, useCallback, useMemo, lazy, Suspense } from 'react';
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
    FileJson,
    Loader2,
    AlertTriangle,
    ZapOff,
    FileSearch,
    DatabaseZap,
    Activity,
    Beaker,
    BarChart3,
    Clock,
    Layers
} from 'lucide-react';
import Tier1Evidence from './Tier1Evidence';
import Tier2Mechanism from './Tier2Mechanism';
import Tier3Causality from './Tier3Causality';
import Tier4Temporal from './Tier4Temporal';
import ConfidenceTracker from './ConfidenceTracker';
import IntegrityBarrier from './IntegrityBarrier';
import EvidenceLineageViewer from './EvidenceLineageViewer';
import PolicyAuthorityCard from './PolicyAuthorityCard';
import ExecutionProfileCard from './ExecutionProfileCard';
import IntelligenceGraph from './IntelligenceGraph';
import RuleFiringTimeline from './RuleFiringTimeline';
import RegistrySnapshot from './RegistrySnapshot';
import CausalityGraph from './CausalityGraph';
import { formatConfidence } from './UIUtils';
import { renderPermissions } from '../../contracts/renderPermissions';
import { EPISTEMIC_COLORS } from '../../contracts/executionTraceSchema';

/**
 * Collapsible Accordion Section — mobile-first.
 */
const AccordionSection = ({ title, icon: Icon, defaultOpen = false, children, id }) => {
    const [open, setOpen] = useState(defaultOpen);
    return (
        <div className="border-b border-neutral-800/40">
            <button
                onClick={() => setOpen(!open)}
                className="w-full flex items-center justify-between px-4 md:px-6 py-3 hover:bg-neutral-800/20 transition-colors"
            >
                <div className="flex items-center gap-2">
                    {Icon && <Icon className="w-3.5 h-3.5 text-neutral-500" />}
                    <span className="text-[10px] font-bold text-neutral-400 uppercase tracking-widest">{title}</span>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 text-neutral-600 transition-transform duration-300 ${open ? 'rotate-180' : ''}`} />
            </button>
            <AnimatePresence initial={false}>
                {open && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.25 }}
                        className="overflow-hidden"
                    >
                        <div className="px-4 md:px-6 pb-5 pt-1">
                            {children}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

/**
 * Baseline Evidence Summary Card
 */
const BaselineEvidenceCard = ({ data }) => {
    if (!data) return null;
    return (
        <div className="grid grid-cols-2 gap-3">
            {[
                { label: 'Total Claims', value: data.total_claims, color: 'text-blue-400' },
                { label: 'Evidence Entries', value: data.total_evidence_entries, color: 'text-emerald-400' },
                { label: 'Highest Study', value: data.highest_study_type, color: 'text-amber-400' },
                { label: 'Empirical Support', value: data.empirical_support_present ? 'Present' : 'Absent', color: data.empirical_support_present ? 'text-emerald-400' : 'text-neutral-500' },
            ].map(item => (
                <div key={item.label} className="bg-black/20 rounded-lg p-3 border border-neutral-800/40">
                    <span className="text-[8px] font-semibold text-neutral-600 uppercase tracking-wider">{item.label}</span>
                    <p className={`text-sm font-bold font-mono mt-0.5 ${item.color}`}>
                        {item.value ?? '—'}
                    </p>
                </div>
            ))}
        </div>
    );
};

/**
 * NutriIntelligencePanel (v1.2.8)
 * 
 * STRICT MODE CONTAINER:
 * - Direct Binding to Backend Epistemic Authority.
 * - Mobile-first responsive layout.
 * - Glassmorphism card aesthetic.
 */
const NutriIntelligencePanel = React.memo(({ uiTrace, expertModeDefault = false }) => {
    // 🛡️ API GOVERNANCE: Version Enforcement (v1.2.8) - UI: v1.2.9
    const currentVersion = uiTrace?.trace_schema_version;
    const isVersionMismatch = currentVersion && currentVersion !== "1.2.8";

    const claims = useMemo(() => (uiTrace?.claims || []), [uiTrace]);
    const metrics = uiTrace?.metrics || {};

    // 🧠 Direct Binding (No inference)
    const isHydrated = uiTrace?.adapter_status === 'success';
    const executionMode = uiTrace?.mode || 'full_trace';
    // Use execution_profile.epistemic_status only (dedup §6)
    const epistemicStatus = uiTrace?.epistemic_status || 'theoretical';
    const isStandby = executionMode === 'non_scientific_discourse' || uiTrace?.domain_type === 'contextual';

    // Confidence tier from raw trace
    const confidenceTier = uiTrace?._raw?.confidence?.tier || 'theoretical';
    // Trace status
    const traceStatus = uiTrace?.status;
    const isComplete = traceStatus === 'COMPLETE' || traceStatus === 'VERIFIED' || traceStatus === 'complete';

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

    const handleCopy = useCallback(() => {
        const text = JSON.stringify(uiTrace?._raw || uiTrace, null, 2);
        navigator.clipboard.writeText(text);
        setCopySuccess(true);
        setTimeout(() => setCopySuccess(false), 2000);
    }, [uiTrace]);

    // Epistemic Color
    const statusColor = useMemo(() => EPISTEMIC_COLORS[epistemicStatus] || '#94a3b8', [epistemicStatus]);

    // Integrity Message
    const integrityMessage = useMemo(() => {
        if (!uiTrace) return "No execution trace recorded";
        if (isStandby) return "Scientific Instrument Standby";
        if (traceStatus === 'INIT') return "Initializing Scientific Workspace...";
        if (traceStatus === 'streaming' || traceStatus === 'STREAMING') return "Reasoning Stream Active...";
        if (isComplete) return "Institutional Audit Terminal";
        return "Deterministic System Telemetry";
    }, [uiTrace, isStandby, traceStatus, isComplete]);

    // Integrity Checks
    const integrityViolation = useMemo(() => {
        if (!uiTrace || isStandby) return null;
        if (uiTrace.adapter_status === "contract_violation") {
            return {
                type: "TRACE CONTRACT VIOLATION",
                missingFields: uiTrace.validation_errors || [],
                context: `run_id: ${uiTrace.run_id || 'NULL'} `
            };
        }
        return null;
    }, [uiTrace, isStandby]);

    if (isVersionMismatch) {
        return (
            <div className="p-4 bg-red-900/20 border border-red-500/50 rounded-xl flex items-center gap-3 text-red-400">
                <AlertTriangle size={20} />
                <div className="text-sm">
                    <span className="font-bold block text-red-300">Trace Contract Error</span>
                    Unsupported schema version: {currentVersion}. Frontend requires 1.2.8.
                </div>
            </div>
        );
    }

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

    const handleClaimSelect = (idx) => setSelectedClaimIdx(idx);

    const currentClaim = claims.length > 0
        ? (claims[selectedClaimIdx] || claims[0])
        : null;

    return (
        <div className="mt-6 border border-neutral-800/60 rounded-xl overflow-hidden bg-gradient-to-b from-neutral-900/40 to-neutral-950/60 backdrop-blur-md animate-fade-in shadow-2xl text-card-foreground intelligence-glass">
            {/* 🛡️ Status & Integrity Banner */}
            <div className={`px-4 py-1.5 border-b border-neutral-800/50 flex items-center gap-2 overflow-hidden ${traceStatus === 'streaming' || traceStatus === 'STREAMING' ? 'bg-blue-500/5' : 'bg-neutral-900/40'}`}>
                {traceStatus === 'streaming' || traceStatus === 'STREAMING' ? (
                    <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />
                ) : integrityViolation ? (
                    <AlertTriangle className="w-3 h-3 text-red-500 animate-pulse" />
                ) : (
                    <ShieldCheck className={`w-3 h-3 ${!uiTrace ? 'text-neutral-700' : 'text-neutral-500'}`} />
                )}

                <p className={`text-[10px] font-mono uppercase tracking-tight truncate flex-1 ${integrityViolation ? 'text-red-500 font-bold' : 'text-neutral-400'}`}>
                    {integrityViolation ? 'TRACE_CONTRACT_VIOLATION' : integrityMessage}
                </p>

                {uiTrace && (
                    <div className="flex items-center gap-3">
                        <div className="hidden md:flex items-center gap-2 pr-2 border-r border-neutral-800/50">
                            <span className="text-[7px] font-mono text-neutral-600 uppercase">Run: {uiTrace.run_id?.split('-')[0] || 'NUL'}</span>
                            <span className="text-[7px] font-mono text-neutral-600 uppercase">Ont: {uiTrace.governance?.ontology_version || '1.2.8'}</span>
                            <span className="text-[7px] font-mono text-neutral-600 uppercase">Enr: {uiTrace.governance?.enrichment_version || '1.2.8'}</span>
                        </div>
                        <span className={`px-2 py-0.5 rounded-full text-[8px] font-bold font-mono border ${traceStatus === 'streaming' || traceStatus === 'STREAMING'
                            ? 'text-blue-400 border-blue-500/20 bg-blue-500/10'
                            : isComplete
                                ? 'text-green-400 border-green-500/20 bg-green-500/10'
                                : 'text-neutral-500 border-neutral-700/50 bg-neutral-800'
                            }`}>
                            {traceStatus ? traceStatus.toUpperCase() : 'UNKNOWN'}
                        </span>
                    </div>
                )}
            </div>

            {/* Header / Trigger */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between p-4 hover:bg-neutral-800/20 transition-all duration-300 group"
            >
                <div className="flex items-center gap-3 text-left">
                    <div className="p-2 rounded-lg bg-accent/10 text-accent group-hover:scale-110 group-hover:bg-accent/20 transition-all duration-500">
                        {executionMode === 'scientific_explanation' || executionMode === 'mechanistic_explainer' ? (
                            <Beaker className="w-4 h-4" />
                        ) : (
                            <Brain className="w-4 h-4" />
                        )}
                    </div>
                    <div className="flex flex-col">
                        <div className="flex items-center gap-2">
                            <h2 className="text-lg md:text-xl font-bold text-white tracking-tight uppercase italic">
                                Nutri Intelligence
                            </h2>
                            <div className={`px-2 py-0.5 rounded border flex items-center gap-1.5 ${executionMode === 'scientific_explanation' || executionMode === 'mechanistic_explainer'
                                ? 'bg-purple-500/10 border-purple-500/20'
                                : 'bg-blue-500/10 border-blue-500/20'
                                }`}>
                                <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${executionMode === 'scientific_explanation' || executionMode === 'mechanistic_explainer' ? 'bg-purple-400' : 'bg-blue-400'
                                    }`} />
                                <span className={`text-[8px] md:text-[9px] font-bold uppercase tracking-widest ${executionMode === 'scientific_explanation' || executionMode === 'mechanistic_explainer' ? 'text-purple-400' : 'text-blue-400'
                                    }`}>
                                    {executionMode === 'scientific_explanation' || executionMode === 'mechanistic_explainer' ? 'SCIENTIFIC' : executionMode.replace(/_/g, ' ')}
                                </span>
                            </div>
                        </div>
                        <p className="text-[9px] md:text-[10px] text-neutral-500 font-bold uppercase tracking-widest ml-1">
                            Audit Terminal • <span style={{ color: statusColor }}>{epistemicStatus.replace(/_/g, ' ')}</span>
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-[10px] font-mono text-neutral-600 group-hover:text-neutral-400 transition-colors uppercase hidden md:inline">
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
                                <button
                                    onClick={toggleRawView}
                                    className={`flex items-center gap-1.5 transition-colors group ${showRawJson ? 'text-accent' : 'text-neutral-500 hover:text-neutral-300'}`}
                                >
                                    <FileJson className="w-3 h-3" />
                                    <span className="font-mono uppercase tracking-tighter">Raw JSON</span>
                                </button>
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
                                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-500/10 border border-green-500/20">Variant: {uiTrace?._raw?.trace_variant || 'legacy'}</span>
                                </div>
                                <pre>{JSON.stringify(uiTrace?._raw || uiTrace, null, 2)}</pre>
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

                                {/* Main Content */}
                                <div className="bg-neutral-900/30">
                                    {isStandby ? (
                                        <div className="w-full py-32 flex flex-col items-center opacity-40">
                                            <MessageSquare className="w-8 h-8 text-neutral-600 mb-4" />
                                            <p className="text-xs font-mono uppercase tracking-widest text-neutral-500">
                                                General Discourse Mode • Scientific Instrument Standby
                                            </p>
                                        </div>
                                    ) : (
                                        <>
                                            {integrityViolation && executionMode !== 'scientific_explanation' && (
                                                <IntegrityBarrier
                                                    type={integrityViolation.type}
                                                    missingFields={integrityViolation.missingFields}
                                                    context={integrityViolation.context}
                                                />
                                            )}

                                            {currentClaim ? (
                                                <>
                                                    {/* Scientific Observation Layer (Full Width) */}
                                                    <AccordionSection title="Scientific Observation" icon={Activity} defaultOpen={false}>
                                                        <EvidenceLineageViewer evidenceSet={currentClaim.evidence} />
                                                    </AccordionSection>

                                                    {/* Causality & Risk (Full Width) */}
                                                    <AccordionSection title="Causality & Risk" badge="Tier 3" defaultExpanded={true}>
                                                        <div className="space-y-4">
                                                            <Tier3Causality uiTrace={uiTrace} claimIdx={0} expertMode={isExpertMode} />
                                                            {uiTrace.causality?.chain?.length > 0 && (
                                                                <div className="pt-4 border-t border-neutral-800/40">
                                                                    <p className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest mb-3">Logic Chain (Deterministic)</p>
                                                                    <CausalityGraph chain={uiTrace.causality.chain} />
                                                                </div>
                                                            )}
                                                        </div>
                                                    </AccordionSection>

                                                    {/* ═══ RESPONSIVE TWO-COLUMN LAYOUT ═══ */}
                                                    <div className={`grid grid-cols-1 lg:grid-cols-2 gap-0 ${integrityViolation && executionMode !== 'scientific_explanation' ? 'blur-sm grayscale pointer-events-none' : ''} space-y-5 lg:space-y-0`}>

                                                        {/* ── LEFT COLUMN ── */}
                                                        <div className="border-r-0 lg:border-r border-neutral-800/40">
                                                            {/* Execution Profile — default open */}
                                                            <AccordionSection title="Execution Profile" icon={Cpu} defaultOpen={true}>
                                                                <ExecutionProfileCard
                                                                    metrics={metrics}
                                                                    epistemicStatus={epistemicStatus}
                                                                    executionMode={executionMode}
                                                                    baselineEvidence={uiTrace.baseline_evidence_summary}
                                                                    confidenceTier={confidenceTier}
                                                                />
                                                            </AccordionSection>

                                                            {/* Confidence Discipline */}
                                                            <AccordionSection title="Confidence Discipline" icon={BarChart3} defaultOpen={false}>
                                                                <ConfidenceTracker
                                                                    uiTrace={uiTrace}
                                                                    claimIdx={selectedClaimIdx}
                                                                    expertMode={isExpertMode}
                                                                />
                                                            </AccordionSection>

                                                            {/* Governance */}
                                                            <AccordionSection title="Governance & Authority" icon={ShieldCheck} defaultOpen={false}>
                                                                <PolicyAuthorityCard
                                                                    governance={uiTrace.governance}
                                                                    registrySnapshot={metrics.registrySnapshot}
                                                                />
                                                            </AccordionSection>

                                                            {/* Temporal Layer */}
                                                            {renderPermissions.canRenderTier4(uiTrace).allowed && (
                                                                <AccordionSection title="Temporal Consistency" icon={Clock} defaultOpen={false}>
                                                                    <Tier4Temporal
                                                                        uiTrace={uiTrace}
                                                                        claimIdx={selectedClaimIdx}
                                                                        expertMode={isExpertMode}
                                                                    />
                                                                </AccordionSection>
                                                            )}
                                                        </div>

                                                        {/* ── RIGHT COLUMN ── */}
                                                        <div>
                                                            {/* Mechanism Graph — default open */}
                                                            <AccordionSection title="Mechanism Topology" icon={Layers} defaultOpen={true}>
                                                                {isComplete ? (
                                                                    <IntelligenceGraph trace={uiTrace} claim={currentClaim} />
                                                                ) : (
                                                                    <div className="py-8 flex flex-col items-center opacity-40">
                                                                        <Loader2 className="w-5 h-5 animate-spin text-neutral-600 mb-2" />
                                                                        <span className="text-[9px] font-mono text-neutral-600 uppercase tracking-widest">
                                                                            Awaiting trace completion...
                                                                        </span>
                                                                    </div>
                                                                )}
                                                            </AccordionSection>

                                                            {/* Mechanism Detail */}
                                                            {renderPermissions.canRenderTier2({ claims: [currentClaim] }).allowed && (
                                                                <AccordionSection title="Mechanistic Detail" icon={Beaker} defaultOpen={false}>
                                                                    <Tier2Mechanism
                                                                        trace={uiTrace}
                                                                        claim={currentClaim}
                                                                        expertMode={isExpertMode}
                                                                    />
                                                                </AccordionSection>
                                                            )}

                                                            {/* Causality */}
                                                            {renderPermissions.canRenderTier3(uiTrace).allowed && (
                                                                <AccordionSection title="Causal Chain" icon={Activity} defaultOpen={false}>
                                                                    <Tier3Causality
                                                                        uiTrace={uiTrace}
                                                                        claimIdx={selectedClaimIdx}
                                                                        expertMode={isExpertMode}
                                                                    />
                                                                </AccordionSection>
                                                            )}

                                                            {/* Baseline Evidence Summary */}
                                                            {uiTrace.baseline_evidence_summary && (
                                                                <AccordionSection title="Baseline Evidence" icon={BarChart3} defaultOpen={false}>
                                                                    <BaselineEvidenceCard data={uiTrace.baseline_evidence_summary} />
                                                                </AccordionSection>
                                                            )}
                                                        </div>
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

                        {/* Knowledge Limitation Declaration */}
                        <div className="mx-4 md:mx-6 mb-4 md:mb-6 mt-2 p-4 rounded-lg bg-neutral-900/40 backdrop-blur-sm border border-neutral-800/40 opacity-80 hover:opacity-100 transition-opacity">
                            <div className="flex items-start gap-3">
                                <Info className="w-3.5 h-3.5 text-neutral-500 mt-0.5 shrink-0" />
                                <div className="space-y-1">
                                    <span className="text-[9px] font-bold text-neutral-500 uppercase tracking-widest">Knowledge Limitation</span>
                                    <p className="text-[10px] text-neutral-600 leading-relaxed italic">
                                        This execution reflects only indexed registry data and formalized policy rules.
                                        Absence of evidence is not evidence of absence.
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Data Provenance Footer */}
                        <div className="px-4 md:px-5 py-3 border-t border-neutral-800 bg-neutral-950 flex items-center justify-between">
                            <div className="flex items-center gap-2 opacity-50">
                                <ShieldCheck className="w-3 h-3 text-neutral-500" />
                                <span className="text-[8px] md:text-[9px] font-mono text-neutral-500 uppercase tracking-widest">
                                    Verified system outputs only.
                                </span>
                            </div>
                            <span className="text-[9px] font-mono text-neutral-700">
                                Trace v{uiTrace?.trace_schema_version || '1.2.8'}
                            </span>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
});

export default NutriIntelligencePanel;

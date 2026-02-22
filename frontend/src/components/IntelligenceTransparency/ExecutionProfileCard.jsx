import React, { useMemo } from 'react';
import {
    Activity,
    ShieldCheck,
    Microscope,
    Scale,
    AlertTriangle,
    Binary,
    Database,
    TrendingUp
} from 'lucide-react';
import { formatMetric, formatConfidence } from './UIUtils';

/**
 * Tier color badge for confidence tier.
 */
const TierBadge = ({ tier }) => {
    const cfg = {
        theoretical: { color: 'text-neutral-400 bg-neutral-500/10 border-neutral-600/30', label: 'Theoretical' },
        speculative: { color: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30', label: 'Speculative' },
        moderate: { color: 'text-blue-400 bg-blue-500/10 border-blue-500/30', label: 'Moderate' },
        strong: { color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30', label: 'Strong' },
        verified: { color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30', label: 'Verified' },
        mechanistic: { color: 'text-purple-400 bg-purple-500/10 border-purple-500/30', label: 'Mechanistic' },
    }[tier] || { color: 'text-neutral-500 bg-neutral-800/20 border-neutral-700/30', label: tier || '—' };

    return (
        <span className={`px-2 py-0.5 rounded border text-[8px] font-black uppercase tracking-widest ${cfg.color}`}>
            {cfg.label}
        </span>
    );
};

const ExecutionProfileCard = ({ metrics, epistemicStatus, executionMode, baselineEvidence, confidenceTier }) => {
    // 🧠 Epistemic Color Mapping
    const getStatusColor = (status) => {
        switch (status) {
            case 'empirical_verified':
            case 'convergent_support': return 'text-blue-400 border-blue-500/30 bg-blue-500/5';
            case 'mechanistically_supported':
            case 'theoretical': return 'text-amber-400 border-amber-500/30 bg-amber-500/5';
            case 'insufficient_evidence':
            case 'fallback_execution': return 'text-neutral-400 border-neutral-500/30 bg-neutral-500/5';
            case 'no_registry_snapshot': return 'text-red-400 border-red-500/30 bg-red-500/5';
            case 'not_applicable': return 'text-neutral-500 border-neutral-700/30 bg-neutral-800/20';
            default: return 'text-red-400 border-red-500/30 bg-red-500/5';
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'empirical_verified':
            case 'convergent_support': return <ShieldCheck className="w-4 h-4" />;
            case 'mechanistically_supported':
            case 'theoretical': return <Microscope className="w-4 h-4" />;
            case 'insufficient_evidence': return <AlertTriangle className="w-4 h-4" />;
            case 'no_registry_snapshot': return <AlertTriangle className="w-4 h-4" />;
            case 'not_applicable': return <Activity className="w-4 h-4 opacity-50" />;
            default: return <Activity className="w-4 h-4" />;
        }
    };

    const breakdown = metrics?.confidence_breakdown || {
        baseline: 0,
        multipliers: [],
        policy_adjustment: 0,
        final: 0
    };

    // Confidence display logic: use fallback if available
    const isDerived = metrics?.ui_confidence_is_derived || false;
    const displayConfidence = isDerived
        ? metrics.ui_confidence_fallback
        : breakdown.final;

    // Evidence Density: derive from baseline_evidence_summary if coverage is 0
    const evidenceDensity = useMemo(() => {
        if (metrics.evidenceCoverage && metrics.evidenceCoverage > 0) {
            return metrics.evidenceCoverage;
        }
        if (baselineEvidence?.total_claims > 0 && baselineEvidence?.total_evidence_entries > 0) {
            return baselineEvidence.total_evidence_entries / baselineEvidence.total_claims;
        }
        return null;
    }, [metrics.evidenceCoverage, baselineEvidence]);

    // Mechanistic Resolution: ensure integer rounding
    const moaDisplay = useMemo(() => {
        if (metrics.moaCoverage === null || metrics.moaCoverage === undefined || isNaN(metrics.moaCoverage)) {
            return null;
        }
        return Math.round(metrics.moaCoverage * 100);
    }, [metrics.moaCoverage]);

    return (
        <div className="intelligence-glass p-3 md:p-5 border border-neutral-800/40 relative overflow-hidden group space-y-6">
            <header className="flex items-center justify-between border-b border-neutral-800 pb-4">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-500/10 rounded-lg">
                        <Binary className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                        <h3 className="text-xs font-black text-neutral-200 uppercase tracking-widest">
                            Execution Profile
                        </h3>
                        <p className="text-[10px] text-neutral-500 font-mono">
                            ID: {metrics.id?.slice(0, 8) || 'N/A'} • v{metrics.trace_schema_version || '1.2.8'}
                        </p>
                    </div>
                </div>
                <div className={`px-3 py-1 rounded-full border text-[10px] font-black uppercase tracking-widest flex items-center gap-2 ${getStatusColor(epistemicStatus)}`}>
                    {getStatusIcon(epistemicStatus)}
                    {epistemicStatus?.replace('_', ' ')}
                </div>
            </header>

            <div className="grid grid-cols-2 gap-6">
                {/* 📊 Metrics Synthesis */}
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <span className="text-[10px] font-medium text-neutral-500 tracking-wide">Evidence Density</span>
                        <span className="text-[10px] font-mono text-neutral-300">
                            {evidenceDensity !== null ? `${Math.round(evidenceDensity * 100)}%` : 'Theoretical-only'}
                        </span>
                    </div>
                    {evidenceDensity !== null && (
                        <div className="w-full h-1 bg-neutral-800 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-blue-500 transition-all duration-1000"
                                style={{ width: `${Math.min((evidenceDensity || 0) * 100, 100)}%` }}
                            />
                        </div>
                    )}

                    <div className="flex items-center justify-between">
                        <span className="text-[10px] font-medium text-neutral-500 tracking-wide">Mechanistic Resolution</span>
                        <span className="text-[10px] font-mono text-neutral-300">
                            {moaDisplay !== null ? `${moaDisplay}%` : 'Partial'}
                        </span>
                    </div>
                    {moaDisplay !== null && (
                        <div className="w-full h-1 bg-neutral-800 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-amber-500 transition-all duration-1000"
                                style={{ width: `${moaDisplay}%` }}
                            />
                        </div>
                    )}
                </div>

                {/* 🛡️ Confidence Analytics */}
                <div className="bg-black/20 rounded-lg p-4 border border-neutral-800/50 flex flex-col justify-center">
                    <div className="text-center">
                        <div className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-1">
                            Response Confidence
                        </div>
                        <div className="text-3xl font-bold text-white font-mono leading-none">
                            {formatConfidence(displayConfidence)}
                        </div>
                        {isDerived && (
                            <div className="mt-1.5 flex items-center justify-center gap-1">
                                <TrendingUp className="w-3 h-3 text-amber-500/60" />
                                <span className="text-[8px] text-amber-500/60 font-mono tracking-wide uppercase">
                                    Derived from Claims
                                </span>
                            </div>
                        )}
                        <div className="mt-2 flex items-center justify-center gap-2">
                            <TierBadge tier={confidenceTier} />
                        </div>
                    </div>
                </div>
            </div>

            {/* 🔍 Diagnostic Basis Panel */}
            <div className="pt-2 border-t border-neutral-800/30">
                <p className="text-[9px] font-semibold text-neutral-600 uppercase tracking-widest mb-3">Epistemic Basis Justification</p>
                <div className="grid grid-cols-4 gap-2">
                    {[
                        { label: 'Evidence', key: 'evidence_present', icon: Database },
                        { label: 'Mechanism', key: 'mechanism_complete', icon: Activity },
                        { label: 'Registry', key: 'registry_valid', icon: ShieldCheck },
                        { label: 'Policy', key: 'policy_intervention', icon: Scale },
                    ].map(feat => {
                        const isActive = metrics.epistemic_basis?.[feat.key];
                        return (
                            <div key={feat.key} className={`relative group flex flex-col items-center gap-1.5 p-2 rounded border transition-all ${isActive
                                ? (feat.key === 'policy_intervention' ? 'bg-amber-500/10 border-amber-500/20 text-amber-500' : 'bg-green-500/10 border-green-500/20 text-green-400')
                                : 'bg-neutral-900 border-neutral-800/50 text-neutral-700 select-none'
                                }`}>
                                <feat.icon className="w-3.5 h-3.5" />
                                <span className="text-[8px] font-bold uppercase tracking-wider">{feat.label}</span>
                                {!isActive && (
                                    <div className="absolute bottom-full mb-2 hidden group-hover:block bg-neutral-950 border border-neutral-800 p-2 rounded text-[9px] text-neutral-400 whitespace-nowrap z-50">
                                        No empirical registry linkage found.
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Primary Limitation Info */}
            {epistemicStatus === 'insufficient_evidence' && (
                <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-3 flex items-start gap-3">
                    <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                    <div className="space-y-1">
                        <p className="text-[10px] font-bold text-red-500 uppercase">Primary Constraint</p>
                        <p className="text-[10px] text-neutral-400 leading-relaxed">
                            No peer-reviewed empirical studies were found in the current registry snapshot
                            ({metrics.registrySnapshot?.hash || 'v1.0'}) that directly evaluate this claim.
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ExecutionProfileCard;

import React from 'react';
import {
    Activity,
    ShieldCheck,
    Microscope,
    Scale,
    AlertTriangle,
    CheckCircle2,
    Binary,
    Database
} from 'lucide-react';
import { formatMetric, formatConfidence } from './UIUtils';

const ExecutionProfileCard = ({ metrics, epistemicStatus, executionMode }) => {
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

    return (
        <div className="bg-neutral-900/40 border border-neutral-800 rounded-lg p-5 space-y-6">
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
                            ID: {metrics.id?.slice(0, 8) || 'N/A'} • v{metrics.trace_schema_version || '1.3'}
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
                            {formatMetric(metrics.evidenceCoverage, 'density')}
                        </span>
                    </div>
                    {/* Only show bar if metric is valid number */}
                    {!isNaN(metrics.evidenceCoverage) && (
                        <div className="w-full h-1 bg-neutral-800 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-blue-500 transition-all duration-1000"
                                style={{ width: `${(metrics.evidenceCoverage || 0) * 100}%` }}
                            />
                        </div>
                    )}

                    <div className="flex items-center justify-between">
                        <span className="text-[10px] font-medium text-neutral-500 tracking-wide">Mechanistic Resolution</span>
                        <span className="text-[10px] font-mono text-neutral-300">
                            {formatMetric(metrics.moaCoverage, 'resolution')}
                        </span>
                    </div>
                    {!isNaN(metrics.moaCoverage) && (
                        <div className="w-full h-1 bg-neutral-800 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-amber-500 transition-all duration-1000"
                                style={{ width: `${(metrics.moaCoverage || 0) * 100}%` }}
                            />
                        </div>
                    )}
                </div>

                {/* 🛡️ Confidence Analytics */}
                <div className="bg-black/20 rounded p-4 border border-neutral-800/50 flex flex-col justify-center">
                    <div className="text-center">
                        <div className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-1">
                            Response Confidence
                        </div>
                        <div className="text-3xl font-bold text-white font-mono leading-none">
                            {formatConfidence(breakdown.final)}
                        </div>
                        <div className="mt-2 flex items-center justify-center gap-1">
                            <Scale className="w-3 h-3 text-neutral-600" />
                            <span className="text-[9px] text-neutral-600 font-mono tracking-wide">
                                Policy Adjusted
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* 🔍 Diagnostic Basis Panel (Requirement Upgrade 27.2) */}
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
                            <div key={feat.key} className={`relative group flex flex-col items-center gap-1.5 p-2 rounded border ${isActive
                                ? (feat.key === 'policy_intervention' ? 'bg-amber-500/10 border-amber-500/20 text-amber-500' : 'bg-green-500/10 border-green-500/20 text-green-400')
                                : 'bg-neutral-900 border-neutral-800/50 text-neutral-700 select-none'
                                }`}>
                                <feat.icon className="w-3.5 h-3.5" />
                                <span className="text-[8px] font-bold uppercase tracking-wider">{feat.label}</span>

                                {/* Inactive Tooltip */}
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

            {/* 🔍 Primary Limitation Info */}
            {epistemicStatus === 'insufficient_evidence' && (
                <div className="bg-red-500/5 border border-red-500/20 rounded p-3 flex items-start gap-3">
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

            {/* 📁 Registry Scope */}
            {metrics.registrySnapshot?.scope && (
                <footer className="pt-2 border-t border-neutral-800/50 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-1.5 opacity-60 group relative cursor-help">
                            <Database className="w-3 h-3 text-neutral-500" />
                            <span className="text-[9px] font-mono text-neutral-500 uppercase">
                                Registry {metrics.registrySnapshot.hash?.slice(0, 8)} (v{metrics.registrySnapshot.version})
                            </span>
                            <div className="absolute bottom-full left-0 mb-2 invisible group-hover:visible bg-neutral-950 border border-neutral-800 p-2 rounded text-[8px] font-mono text-neutral-400 whitespace-nowrap z-50 shadow-2xl">
                                Full Registry SHA256:<br />
                                <span className="text-blue-400">{metrics.registrySnapshot.hash}</span>
                            </div>
                        </div>
                        <div className="flex items-center gap-4 text-[9px] font-mono text-neutral-600 uppercase">
                            <span>{metrics.registrySnapshot.scope.entity_counts?.compounds} Compounds</span>
                            <span>{metrics.registrySnapshot.scope.entity_counts?.processes} Processes</span>
                        </div>
                    </div>
                    <span className="text-[9px] font-mono text-neutral-600">
                        Updated {metrics.registrySnapshot.scope.last_updated}
                    </span>
                </footer>
            )}
        </div>
    );
};

export default ExecutionProfileCard;

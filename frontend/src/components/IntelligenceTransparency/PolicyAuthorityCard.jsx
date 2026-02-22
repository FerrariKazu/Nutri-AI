import React from 'react';
import { ShieldCheck, ShieldAlert, ShieldOff, Info, Database, Clock } from 'lucide-react';

/**
 * PolicyAuthorityCard (v1.2.8)
 * 
 * GOVERNANCE TERMINAL:
 * - 3-state contextual messaging based on backend governance object.
 * - Displays registry snapshot metadata when available.
 */
const PolicyAuthorityCard = ({ governance, registrySnapshot }) => {
    if (!governance) return null;

    const policyId = governance.policy_id || "NONE";
    const isSigned = !!governance.policy_signature_present;
    const isDefaultProfile = policyId === "NONE" && !isSigned;
    const isPresentUnsigned = policyId !== "NONE" && !isSigned;

    // Registry scope parsing
    const scope = registrySnapshot?.scope || {};
    const entityCounts = scope.entity_counts || {};
    const hasScope = Object.keys(entityCounts).length > 0;

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2 px-1">
                <p className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest">Governance & Authority</p>
            </div>

            <div className="p-4 rounded-xl bg-black/30 backdrop-blur-sm border border-neutral-800/60 shadow-inner space-y-4">
                {/* 3-State Governance Badge */}
                {isSigned ? (
                    <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20 flex items-center gap-3">
                        <div className="p-1.5 rounded-lg bg-emerald-500/10">
                            <ShieldCheck className="w-4 h-4 text-emerald-400" />
                        </div>
                        <div>
                            <p className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">Verified Policy Authority</p>
                            <p className="text-[9px] text-emerald-400/60 font-mono mt-0.5">{policyId}</p>
                        </div>
                    </div>
                ) : isPresentUnsigned ? (
                    <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/20 flex items-center gap-3">
                        <div className="p-1.5 rounded-lg bg-amber-500/10">
                            <ShieldAlert className="w-4 h-4 text-amber-400" />
                        </div>
                        <div>
                            <p className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Advisory</p>
                            <p className="text-[9px] text-amber-400/60 leading-relaxed mt-0.5">
                                Policy <span className="font-mono text-amber-300">{policyId}</span> present but not cryptographically signed.
                            </p>
                        </div>
                    </div>
                ) : (
                    <div className="intelligence-glass p-3 rounded-lg bg-neutral-800/30 border border-neutral-700/40 flex items-center gap-3">
                        <div className="p-1.5 rounded-lg bg-neutral-800/50">
                            <Info className="w-4 h-4 text-neutral-500" />
                        </div>
                        <div>
                            <p className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">Informational</p>
                            <p className="text-[9px] text-neutral-500 leading-relaxed mt-0.5">
                                No signed policy attached to this explanation.
                                Mechanistic inference executed under default system profile.
                            </p>
                        </div>
                    </div>
                )}

                {/* Governance Metadata Grid */}
                <div className="grid grid-cols-2 gap-3 text-[10px]">
                    <div className="space-y-1">
                        <span className="text-[8px] font-semibold text-neutral-600 uppercase tracking-wider">Ontology</span>
                        <p className="text-neutral-300 font-mono text-[9px]">v{governance.ontology_version || '—'}</p>
                    </div>
                    <div className="space-y-1">
                        <span className="text-[8px] font-semibold text-neutral-600 uppercase tracking-wider">Enrichment</span>
                        <p className="text-neutral-300 font-mono text-[9px]">v{governance.enrichment_version || '—'}</p>
                    </div>
                    <div className="space-y-1">
                        <span className="text-[8px] font-semibold text-neutral-600 uppercase tracking-wider">Registry Status</span>
                        <p className={`font-mono text-[9px] ${governance.registry_lookup_status === 'matched' ? 'text-emerald-400' :
                            governance.registry_lookup_status === 'error' ? 'text-red-400' :
                                'text-neutral-400'
                            }`}>
                            {governance.registry_lookup_status || '—'}
                        </p>
                    </div>
                    <div className="space-y-1">
                        <span className="text-[8px] font-semibold text-neutral-600 uppercase tracking-wider">Ontology Consistency</span>
                        <p className={`font-mono text-[9px] ${governance.ontology_consistency === false ? 'text-amber-400' : 'text-neutral-400'}`}>
                            {governance.ontology_consistency === false ? 'Divergent' : 'Consistent'}
                        </p>
                    </div>
                </div>

                {/* Registry Scope (if available) */}
                {hasScope && (
                    <div className="pt-3 border-t border-neutral-800/40">
                        <div className="flex items-center gap-1.5 mb-2">
                            <Database className="w-3 h-3 text-neutral-600" />
                            <span className="text-[8px] font-bold text-neutral-600 uppercase tracking-widest">Registry Snapshot</span>
                        </div>
                        <div className="flex items-center gap-4 text-[9px] font-mono text-neutral-500">
                            {entityCounts.compounds != null && <span>{entityCounts.compounds} Compounds</span>}
                            {entityCounts.processes != null && <span>{entityCounts.processes} Processes</span>}
                            {entityCounts.physical_states != null && <span>{entityCounts.physical_states} States</span>}
                        </div>
                        {scope.last_updated && (
                            <div className="flex items-center gap-1.5 mt-1.5 text-[8px] text-neutral-600 font-mono">
                                <Clock className="w-2.5 h-2.5" />
                                <span>Updated {scope.last_updated}</span>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default PolicyAuthorityCard;

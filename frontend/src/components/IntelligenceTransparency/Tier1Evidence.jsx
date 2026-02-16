import React from 'react';
import { Database, FlaskConical, AlertCircle, Hash, Users, Microscope, Scale, History, ExternalLink, ShieldCheck } from 'lucide-react';
import { TierBadge, Tooltip } from './UIUtils';
import { renderPermissions } from '../../contracts/renderPermissions';

/**
 * Tier1Evidence
 * 
 * STRICT MODE:
 * - No defaults for source.
 * - Explicit "Unavailable" if data missing.
 * - No synthetic confidence.
 */
const Tier1Evidence = React.memo(({ trace, claim, metrics, expertMode }) => {
    // 1. Permission Gate - UNBREAKABLE: Never return null.
    // We render available markers instead.
    const hasPermission = renderPermissions.canRenderTier1(trace).allowed;

    // 2. Strict Data Access
    // Explicit Null Handling for Confidence (New Structured Object)
    const confObj = claim.confidence;
    const hasConfidence = confObj !== undefined && confObj !== null;
    const confidenceVal = hasConfidence ? Math.round((confObj.current ?? confObj) * 100) : null;
    const policyId = confObj?.policy_id;
    const policyVersion = confObj?.policy_version;
    const breakdown = confObj?.breakdown;

    // Strict Source — handle both string and object forms from backend
    const sourceText = typeof claim.source === 'object' && claim.source !== null
        ? claim.source.name || JSON.stringify(claim.source)
        : claim.source;

    // Evidence Set
    const evidenceSet = claim.evidence || [];
    const hasEvidence = evidenceSet.length > 0;

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <TierBadge tier={1} label="Evidence" />
                    <Database className="w-3 h-3 text-green-400 opacity-50" />
                    <Tooltip text="Raw data verification layer." />
                </div>
                {hasConfidence ? (
                    <div className="flex flex-col items-end gap-1">
                        <span className={`text-[9px] font-mono px-2 py-0.5 rounded border ${confidenceVal > 80 ? 'text-green-400 bg-green-500/10 border-green-500/20' :
                            confidenceVal > 50 ? 'text-amber-400 bg-amber-500/10 border-amber-500/20' :
                                'text-neutral-500 bg-neutral-900 border-neutral-800'
                            }`}>
                            CONFIDENCE: {confidenceVal}%
                        </span>
                        {policyId && (
                            <span className="text-[7px] font-mono text-neutral-500 uppercase tracking-tighter">
                                Policy: {policyId} / v{policyVersion}
                            </span>
                        )}
                    </div>
                ) : (
                    <span className="text-[9px] font-mono text-neutral-500 bg-neutral-900 px-2 py-0.5 rounded border border-neutral-800">
                        CONFIDENCE: NULL
                    </span>
                )}
            </div>

            <p className="text-sm text-neutral-300 leading-relaxed">
                Source: <span className="text-white font-medium">{sourceText || 'NULL'}</span>
                {claim.evidence_type && (
                    <span className="ml-2 text-[8px] font-mono text-neutral-500 border border-neutral-800 px-1 rounded uppercase">
                        {claim.evidence_type}
                    </span>
                )}
            </p>

            {claim.estimated_via_ontology && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/5 border border-amber-500/10">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-500/60" />
                    <p className="text-[10px] text-amber-500/80 font-medium">
                        ⚠ Estimated via ontology expansion
                    </p>
                </div>
            )}

            {/* Structured Evidence Records (Phase 7 UI Evolution) */}
            {hasEvidence && (
                <div className="space-y-3">
                    <div className="flex items-center gap-1.5 px-0.5">
                        <p className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest">Scientific Evidence Base</p>
                    </div>
                    <div className="grid grid-cols-1 gap-2">
                        {evidenceSet.map((record, i) => (
                            <div key={i} className="p-3 rounded-lg bg-neutral-900/50 border border-neutral-800 flex flex-col gap-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <div className={`p-1 rounded ${record.study_type === 'meta-analysis' ? 'bg-purple-500/10 text-purple-400' :
                                            record.study_type === 'rct' ? 'bg-blue-500/10 text-blue-400' :
                                                'bg-neutral-800 text-neutral-400'
                                            }`}>
                                            {record.study_type === 'meta-analysis' || record.study_type === 'systematic-review' ? <Scale className="w-3 h-3" /> :
                                                record.study_type === 'rct' || record.study_type === 'observational' ? <Users className="w-3 h-3" /> :
                                                    <Microscope className="w-3 h-3" />}
                                        </div>
                                        <div>
                                            <p className="text-[10px] font-bold text-neutral-200 uppercase">{record.study_type.replace('-', ' ')}</p>
                                            <p className="text-[9px] text-neutral-500 font-mono">{record.source_identifier}</p>
                                        </div>
                                    </div>
                                    <div className={`text-[8px] font-mono px-1.5 py-0.5 rounded border ${record.evidence_grade === 'strongest' ? 'text-purple-400 border-purple-500/30' :
                                        record.evidence_grade === 'strong' ? 'text-blue-400 border-blue-500/30' :
                                            record.evidence_grade === 'weak' ? 'text-amber-500/60 border-amber-500/20' :
                                                'text-neutral-500 border-neutral-800'
                                        }`}>
                                        {record.evidence_grade.toUpperCase()}
                                    </div>
                                </div>

                                <div className="flex items-center gap-4 text-[10px]">
                                    <div className="flex items-center gap-1 text-neutral-400">
                                        <Users className="w-3 h-3 opacity-50" />
                                        <span>n={record.n || 'N/A'}</span>
                                    </div>
                                    <div className="flex items-center gap-1 text-neutral-400">
                                        <History className="w-3 h-3 opacity-50" />
                                        <span>{record.publication_year || 'N/A'}</span>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <div className={`w-1.5 h-1.5 rounded-full ${record.effect_direction === 'positive' ? 'bg-green-500' :
                                            record.effect_direction === 'negative' ? 'bg-red-500' :
                                                'bg-neutral-500'
                                            }`} />
                                        <span className="capitalize text-neutral-500">{record.effect_direction} Effect</span>
                                    </div>
                                </div>

                                {record.contradiction_links && record.contradiction_links.length > 0 && (
                                    <div className="mt-1 flex items-center gap-1.5 text-[9px] text-red-400/80 bg-red-400/5 px-2 py-1 rounded border border-red-400/10">
                                        <AlertCircle className="w-2.5 h-2.5" />
                                        <span>Supported by contradicting data ({record.contradiction_links.length} sources)</span>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {!hasEvidence && (
                <div className="space-y-2">
                    <div className="flex items-center gap-1.5 px-0.5">
                        <p className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest">Active Data Indices</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {(expertMode && metrics.sourceContribution && Object.keys(metrics.sourceContribution).length > 0
                            ? Object.keys(metrics.sourceContribution)
                            : [sourceText]).filter(Boolean).map((src, i) => (
                                <div key={i} className="px-2.5 py-1 rounded bg-neutral-800/40 border border-neutral-700/30 flex items-center gap-2.5 cursor-default">
                                    <span className="text-[10px] text-neutral-400 font-mono tracking-tight">{typeof src === 'object' ? (src.name || JSON.stringify(src)) : src}</span>
                                    {expertMode && metrics.sourceContribution && (
                                        <span className="text-[9px] text-green-400 font-bold font-mono">
                                            {(metrics.sourceContribution[src] || 0)}%
                                        </span>
                                    )}
                                </div>
                            ))}

                        {(!claim.source && (!metrics.sourceContribution || Object.keys(metrics.sourceContribution).length === 0)) && (
                            <span className="text-[10px] text-neutral-600 font-mono italic">No source metadata</span>
                        )}
                    </div>
                </div>
            )}

            {/* PubChem Proof Section */}
            {metrics.pubchemUsed && (
                <div className="mt-4 p-3 rounded-lg bg-green-500/5 border border-green-500/10 flex items-start gap-4 shadow-inner">
                    <FlaskConical className="w-4 h-4 text-green-400 shrink-0 mt-0.5" />
                    <div className="flex-1">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <p className="text-[10px] font-bold text-green-400 uppercase tracking-widest">Molecular Identity Verified</p>
                            </div>
                            <span className="text-[8px] font-mono text-green-400/50 px-1.5 py-0.5 border border-green-500/20 rounded-full">P0 ENFORCED</span>
                        </div>
                        <div className="flex items-center gap-2 mt-1.5">
                            <Hash className="w-2.5 h-2.5 text-neutral-600" />
                            <p className="text-[9px] text-neutral-500 font-mono truncate max-w-[240px]">
                                {metrics.proofHash || 'Verified via PubChem PUG-REST protocol'}
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
});

export default Tier1Evidence;

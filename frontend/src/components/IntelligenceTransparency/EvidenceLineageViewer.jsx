import React from 'react';
import { Microscope, Users, History, AlertCircle, ExternalLink, Link2, FileSearch } from 'lucide-react';

/**
 * EvidenceLineageViewer
 * 
 * FACTUAL GROUNDING TERMINAL:
 * - Verbatim listing of scientific evidence.
 * - Raw identifiers for expert verification (UniProt, PubChem).
 * - No interpretation or summarization.
 */
const EvidenceLineageViewer = ({ evidenceSet }) => {
    if (!evidenceSet || evidenceSet.length === 0) {
        return (
            <div className="p-4 rounded-lg bg-neutral-900/50 border border-neutral-800 flex items-center gap-3">
                <FileSearch className="w-4 h-4 text-neutral-500" />
                <p className="text-[10px] font-medium text-neutral-500 uppercase tracking-widest">
                    No Empirical Grounding Available
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            <div className="flex items-center gap-2 px-1">
                <p className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest">Empirical Grounding (Verbatim)</p>
            </div>

            <div className="grid grid-cols-1 gap-3">
                {evidenceSet.map((record, i) => (
                    <div key={i} className="group p-3 rounded-lg bg-black/40 border border-neutral-800 hover:border-neutral-700 transition-colors">
                        <div className="flex items-start justify-between">
                            <div className="flex items-center gap-3">
                                <div className={`p-1.5 rounded-md ${record.study_type === 'meta-analysis' || record.study_type === 'systematic-review' ? 'bg-purple-500/10 text-purple-400' :
                                    record.study_type === 'rct' ? 'bg-blue-500/10 text-blue-400' :
                                        'bg-neutral-800 text-neutral-400'
                                    }`}>
                                    {record.study_type === 'meta-analysis' || record.study_type === 'systematic-review' ? <Microscope className="w-3.5 h-3.5" /> :
                                        record.study_type === 'rct' || record.study_type === 'observational' ? <Users className="w-3.5 h-3.5" /> :
                                            <FileSearch className="w-3.5 h-3.5" />}
                                </div>
                                <div className="space-y-0.5">
                                    <p className="text-[10px] font-bold text-neutral-200 uppercase tracking-wide">
                                        {record.study_type ? record.study_type.replace(/-/g, ' ') : 'Classification Pending'}
                                    </p>
                                    <div className="flex items-center gap-2">
                                        <span className="text-[9px] text-neutral-500 font-mono">ID: {record.source_identifier}</span>
                                        {record.source_identifier?.startsWith('PMID:') && (
                                            <a
                                                href={`https://pubmed.ncbi.nlm.nih.gov/${record.source_identifier.split(':')[1]}/`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-blue-500/50 hover:text-blue-400 transition-colors"
                                            >
                                                <ExternalLink className="w-2.5 h-2.5" />
                                            </a>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div className={`text-[8px] font-bold px-1.5 py-0.5 rounded border ${record.evidence_grade === 'strongest' ? 'text-purple-400 border-purple-500/30 bg-purple-500/5' :
                                record.evidence_grade === 'strong' ? 'text-blue-400 border-blue-500/30 bg-blue-500/5' :
                                    record.evidence_grade === 'weak' ? 'text-amber-500/60 border-amber-500/20' :
                                        'text-neutral-500 border-neutral-800'
                                }`}>
                                {String(record.evidence_grade).toUpperCase()}
                            </div>
                        </div>

                        <div className="mt-3 grid grid-cols-3 gap-2 border-t border-neutral-800/50 pt-3">
                            <div className="flex items-center gap-1.5 text-[9px] text-neutral-400">
                                <Users className="w-3 h-3 opacity-40 text-blue-400" />
                                <span className="font-mono">n={record.n ?? '—'}</span>
                            </div>
                            <div className="flex items-center gap-1.5 text-[9px] text-neutral-400">
                                <History className="w-3 h-3 opacity-40 text-amber-500" />
                                <span className="font-mono">yr={record.publication_year ?? '—'}</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <div className={`w-1.5 h-1.5 rounded-full ${record.effect_direction === 'positive' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]' :
                                    record.effect_direction === 'negative' ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]' :
                                        'bg-neutral-500'
                                    }`} />
                                <span className={`text-[9px] font-bold uppercase tracking-tight ${record.effect_direction === 'positive' ? 'text-green-500/80' :
                                    record.effect_direction === 'negative' ? 'text-red-500/80' :
                                        'text-neutral-600'
                                    }`}>
                                    {record.effect_direction}
                                </span>
                            </div>
                        </div>

                        {/* Raw Provenance IDs (UniProt/PubChem etc.) */}
                        <div className="mt-2.5 space-y-1">
                            {record.uniprot_id && (
                                <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-neutral-900 border border-neutral-800/50">
                                    <Link2 className="w-2.5 h-2.5 text-neutral-600" />
                                    <span className="text-[8px] font-mono text-neutral-500 uppercase">UniProt:</span>
                                    <span className="text-[8px] font-mono text-blue-400/70">{record.uniprot_id}</span>
                                </div>
                            )}
                            {record.pubchem_cid && (
                                <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-neutral-900 border border-neutral-800/50">
                                    <Link2 className="w-2.5 h-2.5 text-neutral-600" />
                                    <span className="text-[8px] font-mono text-neutral-500 uppercase">PubChem CID:</span>
                                    <span className="text-[8px] font-mono text-green-400/70">{record.pubchem_cid}</span>
                                </div>
                            )}
                        </div>

                        {record.contradiction_links && record.contradiction_links.length > 0 && (
                            <div className="mt-2.5 flex items-center gap-2 text-[8px] text-red-500/80 bg-red-500/5 px-2.5 py-1.5 rounded border border-red-500/20">
                                <AlertCircle className="w-2.5 h-2.5 animate-pulse" />
                                <span className="font-bold uppercase tracking-tight">
                                    Contradictory Evidence Noted ({record.contradiction_links.length})
                                </span>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default EvidenceLineageViewer;

import React from 'react';
import { ShieldCheck, User, Landmark, Calendar, Hash, Lock, Info } from 'lucide-react';

/**
 * PolicyAuthorityCard
 * 
 * GOVERNANCE TERMINAL:
 * - Exposes who had the right to judge.
 * - Renders author, review board, approval date, and tamper-evidence (hash/attestation).
 * - Displays the selection reason to remove "invisible bias."
 */
const PolicyAuthorityCard = ({ policy }) => {
    if (!policy) return null;

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2 px-1">
                <p className="text-[9px] font-mono text-neutral-500 uppercase tracking-widest">Policy Authority (Governance)</p>
            </div>

            <div className="p-4 rounded-xl bg-black/40 border border-neutral-800 shadow-inner">
                <div className="flex items-start justify-between mb-4">
                    <div className="space-y-1">
                        <div className="flex items-center gap-2">
                            <h3 className="text-xs font-black text-neutral-200 uppercase tracking-tight">
                                {policy.policy_id}
                            </h3>
                            <span className="text-[8px] font-mono bg-neutral-800 text-neutral-400 px-1.5 py-0.5 rounded border border-neutral-700">
                                v{policy.policy_version}
                            </span>
                        </div>
                        <p className="text-[9px] font-mono text-neutral-500 uppercase">Reason: {policy.selection_reason || 'UNDEFINED'}</p>
                    </div>
                    <ShieldCheck className="w-5 h-5 text-blue-500/50" />
                </div>

                <div className="grid grid-cols-2 gap-y-3 gap-x-6 text-[10px]">
                    <div className="space-y-1">
                        <div className="flex items-center gap-1.5 text-neutral-500">
                            <User className="w-3 h-3" />
                            <span className="uppercase text-[8px] font-bold">Author</span>
                        </div>
                        <p className="text-neutral-300 font-mono tracking-tighter">{policy.author || 'NULL'}</p>
                    </div>

                    <div className="space-y-1">
                        <div className="flex items-center gap-1.5 text-neutral-500">
                            <Landmark className="w-3 h-3" />
                            <span className="uppercase text-[8px] font-bold">Review Board</span>
                        </div>
                        <p className="text-neutral-300 font-mono tracking-tighter">{policy.review_board || 'NULL'}</p>
                    </div>

                    <div className="space-y-1">
                        <div className="flex items-center gap-1.5 text-neutral-500">
                            <Calendar className="w-3 h-3" />
                            <span className="uppercase text-[8px] font-bold">Approval Date</span>
                        </div>
                        <p className="text-neutral-300 font-mono tracking-tighter">{policy.approval_date || 'NULL'}</p>
                    </div>

                    <div className="space-y-1">
                        <div className="flex items-center gap-1.5 text-neutral-500">
                            <Hash className="w-3 h-3" />
                            <span className="uppercase text-[8px] font-bold">Document Hash</span>
                        </div>
                        <p className="text-blue-400/60 font-mono text-[8px] truncate max-w-[120px]" title={policy.policy_hash}>
                            {policy.policy_hash || 'NON_DETERMINISTIC'}
                        </p>
                    </div>
                </div>

                {policy.attestation && (
                    <div className="mt-4 p-2.5 rounded bg-blue-500/5 border border-blue-500/10 flex items-start gap-3">
                        <Lock className="w-3 h-3 text-blue-500 shrink-0 mt-0.5" />
                        <div>
                            <p className="text-[8px] font-bold text-blue-400 uppercase mb-0.5">Formal Attestation</p>
                            <p className="text-[9px] text-blue-400/70 font-mono leading-tight">{policy.attestation}</p>
                        </div>
                    </div>
                )}

                {!policy.policy_hash && (
                    <div className="mt-4 p-2.5 rounded bg-red-500/5 border border-red-500/10 flex items-center gap-3">
                        <Info className="w-3 h-3 text-red-500" />
                        <p className="text-[9px] font-bold text-red-500 uppercase">Warning: Unsigned Policy Logic</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default PolicyAuthorityCard;

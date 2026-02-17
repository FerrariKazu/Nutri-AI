import React, { useState, useEffect } from 'react';
import { uniprotClient } from '../../utils/UniProtClient';
import { DatabaseZap, ExternalLink, Loader2, Info } from 'lucide-react';

const UniProtAnnotation = ({ uniprotId }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let isMounted = true;

        async function fetchAnnotation() {
            setLoading(true);
            const result = await uniprotClient.getProteinAnnotation(uniprotId);
            if (isMounted) {
                setData(result);
                setLoading(false);
            }
        }

        if (uniprotId) {
            fetchAnnotation();
        }

        return () => { isMounted = false; };
    }, [uniprotId]);

    if (!uniprotId) return null;

    return (
        <div className="mt-4 p-4 rounded-lg bg-purple-500/5 border border-purple-500/10 space-y-3">
            <header className="flex items-center justify-between border-b border-purple-500/10 pb-2">
                <div className="flex items-center gap-2">
                    <DatabaseZap className="w-3.5 h-3.5 text-purple-400" />
                    <span className="text-[10px] font-black text-purple-400 uppercase tracking-widest">External Protein Annotation</span>
                </div>
                <div className="px-2 py-0.5 rounded-full bg-neutral-900 border border-neutral-800 text-[8px] font-mono text-neutral-500 uppercase">
                    UniProt KB v1.1
                </div>
            </header>

            {loading ? (
                <div className="flex items-center gap-2 py-2">
                    <Loader2 className="w-3 h-3 text-purple-400 animate-spin" />
                    <span className="text-[10px] text-neutral-500 font-mono">Fetching external biological context...</span>
                </div>
            ) : data?.error ? (
                <div className="flex items-center gap-2 py-2 text-neutral-500">
                    <Info className="w-3 h-3" />
                    <span className="text-[10px] italic">External annotation service unavailable. Core trace integrity preserved.</span>
                </div>
            ) : (
                <div className="space-y-3 animate-fade-in">
                    <div className="flex items-start justify-between gap-4">
                        <div className="space-y-1">
                            <h6 className="text-[11px] font-bold text-neutral-200 uppercase tracking-tight">{data.name}</h6>
                            <p className="text-[9px] font-mono text-neutral-400">Gene: {data.gene} • Organism: {data.organism}</p>
                        </div>
                        <a
                            href={`https://www.uniprot.org/uniprotkb/${uniprotId}/entry`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1.5 rounded hover:bg-white/5 transition-colors"
                        >
                            <ExternalLink className="w-3 h-3 text-purple-400/60" />
                        </a>
                    </div>

                    <div className="bg-black/20 p-2.5 rounded border border-purple-500/5">
                        <p className="text-[10px] text-neutral-400 leading-relaxed">
                            {data.function}
                        </p>
                    </div>

                    <footer className="pt-1 flex items-center justify-between opacity-40">
                        <span className="text-[8px] font-mono text-neutral-500 tracking-tighter uppercase">
                            Architecture: Isolated Provider
                        </span>
                        <span className="text-[8px] font-mono text-neutral-500 uppercase">
                            Fetched {new Date(data.fetchedAt).toLocaleTimeString()}
                        </span>
                    </footer>
                </div>
            )}
        </div>
    );
};

export default UniProtAnnotation;

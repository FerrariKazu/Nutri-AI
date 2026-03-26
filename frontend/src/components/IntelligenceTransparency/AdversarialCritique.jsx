import React from 'react';
import { Swords, ShieldAlert, CheckCircle2, AlertTriangle, HelpCircle } from 'lucide-react';

/**
 * AdversarialCritique - Renders structured critique from the AdversarialAgent.
 */
const AdversarialCritique = ({ critique }) => {
  if (!critique) return (
    <div className="flex flex-col items-center justify-center p-8 text-neutral-500 opacity-50 h-full">
      <Swords className="w-12 h-12 mb-4" />
      <p className="font-mono text-xs uppercase tracking-widest">No adversarial pass required for this tier.</p>
    </div>
  );

  const getVerdictColor = (verdict) => {
    const v = verdict?.toLowerCase();
    if (v?.includes('rejected') || v?.includes('invalid')) return 'text-red-500 border-red-500/20 bg-red-500/5';
    if (v?.includes('weak') || v?.includes('caution')) return 'text-amber-500 border-amber-500/20 bg-amber-500/5';
    if (v?.includes('strong') || v?.includes('valid')) return 'text-green-500 border-green-500/20 bg-green-500/5';
    return 'text-neutral-400 border-neutral-800 bg-neutral-900/50';
  };

  const getVerdictIcon = (verdict) => {
    const v = verdict?.toLowerCase();
    if (v?.includes('rejected') || v?.includes('invalid')) return <ShieldAlert className="w-5 h-5" />;
    if (v?.includes('weak') || v?.includes('caution')) return <AlertTriangle className="w-5 h-5" />;
    if (v?.includes('strong') || v?.includes('valid')) return <CheckCircle2 className="w-5 h-5" />;
    return <HelpCircle className="w-5 h-5" />;
  };

  return (
    <div className="adversarial-pass p-6 space-y-6 animate-fade-in overflow-y-auto max-h-[70vh] bg-black/20">
      {/* Header Verdict Card */}
      <div className={`p-4 rounded-lg border flex items-center justify-between ${getVerdictColor(critique.verdict)} shadow-lg backdrop-blur-md`}>
        <div className="flex items-center gap-3">
          {getVerdictIcon(critique.verdict)}
          <div className="flex flex-col">
            <span className="text-[10px] uppercase font-mono tracking-tighter opacity-70 text-neutral-400">Adversarial Verdict</span>
            <span className="text-lg font-serif font-bold tracking-tight">{critique.verdict || 'PENDING'}</span>
          </div>
        </div>
        <div className="flex flex-col items-end">
           <span className="text-[10px] uppercase font-mono tracking-tighter opacity-70 text-neutral-400">Confidence Delta</span>
           <span className="text-sm font-mono font-bold">
             {critique.confidence_delta > 0 ? '+' : ''}{critique.confidence_delta || 0}%
           </span>
        </div>
      </div>

      {/* Core Critique Area */}
      <div className="space-y-4">
        <div className="bg-neutral-900/30 p-5 rounded-lg border border-neutral-800/50 backdrop-blur-sm shadow-inner">
          <h4 className="text-[10px] uppercase font-mono tracking-widest text-neutral-500 mb-3 flex items-center gap-2">
            <Swords className="w-3 h-3 text-accent" /> Adversarial Attack Report
          </h4>
          <p className="text-sm text-neutral-200 leading-relaxed font-sans italic opacity-85">
            "{critique.critique || 'The critic found no significant flaws in the primary mechanism.'}"
          </p>
        </div>

        {critique.missing_context && (
          <div className="bg-red-950/10 p-5 rounded-lg border border-red-500/10 shadow-sm relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-1 h-full bg-red-500/40 group-hover:bg-red-500 transition-colors"></div>
            <h4 className="text-[10px] uppercase font-mono tracking-widest text-red-400/80 mb-2">Missing Context / Flaws</h4>
            <p className="text-sm text-neutral-400 leading-relaxed">
              {critique.missing_context}
            </p>
          </div>
        )}

        {critique.alternatives && critique.alternatives.length > 0 && (
          <div className="bg-blue-950/10 p-5 rounded-lg border border-blue-500/10 shadow-sm relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-1 h-full bg-blue-500/40 group-hover:bg-blue-500 transition-colors"></div>
            <h4 className="text-[10px] uppercase font-mono tracking-widest text-blue-400/80 mb-3">Alternative Hypotheses</h4>
            <ul className="space-y-3">
              {critique.alternatives.map((alt, i) => (
                <li key={i} className="text-xs text-neutral-300 flex items-start gap-3 opacity-80 hover:opacity-100 transition-opacity">
                  <span className="text-blue-500 shrink-0 font-bold"># {i+1}</span>
                  <span className="leading-normal">{alt}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Footer System Audit */}
      <div className="pt-6 border-t border-neutral-800/50 flex items-center justify-between opacity-30">
        <span className="text-[8px] font-mono tracking-widest uppercase text-neutral-500 flex items-center gap-2">
          Mechanistic Integrity: <span className={critique.verdict === 'Strongly Valid' ? 'text-green-500' : 'text-amber-500'}>{critique.verdict === 'Strongly Valid' ? 'PASS' : 'WARN'}</span>
        </span>
        <span className="text-[8px] font-mono tracking-widest uppercase text-neutral-500">Model: adversarial-critic-v2</span>
      </div>
    </div>
  );
};

export default AdversarialCritique;

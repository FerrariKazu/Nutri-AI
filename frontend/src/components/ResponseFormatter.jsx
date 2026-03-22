import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function stripMarkdownJson(text) {
  if (!text) return "";
  let clean = text.trim();
  if (clean.startsWith("```json")) {
    clean = clean.substring(7);
  }
  if (clean.startsWith("```")) {
    clean = clean.substring(3);
  }
  if (clean.endsWith("```")) {
    clean = clean.substring(0, clean.length - 3);
  }
  return clean.trim();
}

function isCompleteJSON(text) {
  if (!text) return false;
  const trimmed = stripMarkdownJson(text);
  return trimmed.startsWith("{") && trimmed.endsWith("}");
}

// Helper to convert structured sections into JSX using ReactMarkdown
function renderMarkdown(content) {
  if (!content) return null;
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]}>
      {content}
    </ReactMarkdown>
  );
}

// Split narrative by specified markers and wrap in headers
function renderScientificNarrative(narrative) {
  if (!narrative) return null;

  // Split by the new 7-section markers
  const sections = narrative.split(/(?=\*\*(?:Core Insight|Explanation|Most Important Driver|Secondary Factors|Why This Matters|Nuance & Exceptions|Confidence):?\*\*)/i);

  return sections.map((section, idx) => {
    const match = section.match(/^\*\*(.*?):?\*\*/);
    if (match) {
      const title = match[1].trim();
      const content = section.replace(/^\*\*(.*?):?\*\*/, '').trim();
      
      const isCoreInsight = title.toLowerCase().includes('core insight');
      const isConfidence = title.toLowerCase().includes('confidence');

      return (
        <div key={idx} className={`mb-4 ${isCoreInsight ? 'p-3 bg-blue-900/20 border border-blue-800/30 rounded-lg' : ''}`}>
          <h3 className={`text-md sm:text-lg font-bold mb-2 ${isCoreInsight ? 'text-blue-300' : isConfidence ? 'text-neutral-400' : 'text-blue-400 dark:text-blue-300'}`}>
            {title}
          </h3>
          <div className={`prose prose-sm prose-invert ${isCoreInsight ? 'text-neutral-200 font-medium' : 'text-neutral-300'}`}>
            {renderMarkdown(content)}
          </div>
        </div>
      );
    }
    return (
      <div key={idx} className="mb-4 prose prose-sm prose-invert text-neutral-300">
        {renderMarkdown(section.trim())}
      </div>
    );
  });
}

// extractMacros function removed to rely solely on structured LLM answer text

const ResponseFormatter = React.memo(({ text, isStreaming }) => {
  if (!text) return null;

  // 2. DIAGNOSTIC LOGGING (REQUESTED)
  console.log('[TOKEN_RECEIVED] length=', text.length, 'preview=', text.substring(0, 100));

  // Determine if we should use dark mode classes (prose-invert)
  // Since we don't have easy access to theme context here, we'll use a safer approach:
  // Only use prose-invert if we are sure we are on a dark background.
  // For now, let's make it more robust.
  const proseClass = "prose prose-sm prose-invert max-w-none text-neutral-200 animate-fade-in leading-relaxed";

  // STEP 1: Streaming + JSON Parse Safety
  if (isStreaming || !isCompleteJSON(text)) {
    return (
      <div className={proseClass}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      </div> // Fallback when incomplete
    );
  }

  // STEP 2: Safe parsing
  let data;
  try {
    const cleanJson = stripMarkdownJson(text);
    data = JSON.parse(cleanJson);
    console.log('[TOKEN_PARSED]', data);
  } catch (e) {
    console.log('[TOKEN_PARSE_FAILED]', e.message, 'raw=', text.substring(0, 200));
    // Failsafe: if looks complete but fails to parse
    return (
      <div className={proseClass}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      </div> 
    );
  }

  const { scientific_response, nutritional_response, confidence, pipeline_failure, epistemic_state } = data;

  // 3. SUPPRESSION CHECK (REQUESTED)
  // Ensure that UNCERTAIN or "failed" core_insight does NOT suppress the entire response.
  const hasFailedInsight = scientific_response?.core_insight?.toLowerCase().includes("failed");
  if (epistemic_state === "UNCERTAIN" || hasFailedInsight) {
    console.log('[EFL_DEBUG] Rendering uncertain/failed response instead of suppressing.', { epistemic_state, hasFailedInsight });
  }

  // TASK 7: FAIL-SAFE
  if (!scientific_response && !nutritional_response) {
    console.log("FAIL-SAFE: No structured responses found, falling back to markdown");
    return (
      <div className={proseClass}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      </div> 
    );
  }

  const isLowConfidence = confidence !== undefined && confidence < 0.4;

  return (
    <div className="nutri-structured-response flex flex-col gap-6 w-full animate-fade-in text-neutral-900 dark:text-neutral-100">

      {/* --- Pipeline Failure Banner --- */}
      {pipeline_failure && (
        <div className="flex flex-col gap-1 p-3 border rounded-lg text-sm bg-amber-950/40 border-amber-900/50 text-amber-400">
          <div className="flex items-center gap-2 font-bold uppercase tracking-wider text-[10px]">
             <span>⚠️</span> Pipeline Failure
          </div>
          <div className="opacity-90">
            Reasoning pipeline was unable to reach high-confidence consensus.
          </div>
        </div>
      )}

      {/* --- Scientific Section --- */}
      {scientific_response && (
        <div className="scientific-section pl-0 border-0 rounded-none bg-transparent">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-2 border-b border-neutral-700/50">
            <h2 className="text-lg font-semibold text-neutral-200">
              Scientific Explanation
            </h2>
            <span className="text-[10px] text-neutral-500 font-mono self-start sm:self-auto uppercase tracking-widest">
              MECHANISTIC MODEL
            </span>
          </div>
          
          {(scientific_response.narrative || !scientific_response.core_insight) ? (
            renderScientificNarrative(scientific_response.narrative || scientific_response.explanation)
          ) : (
            <div className="space-y-4">
              {scientific_response.core_insight && (
                <div className="p-4 bg-neutral-800/60 border-l-2 border-neutral-400 rounded-r-lg mb-4">
                  <p className="text-xs font-semibold uppercase tracking-widest text-neutral-500 mb-1 mt-4">Core Insight</p>
                  <div className="prose prose-sm prose-invert text-neutral-100 font-medium text-base">
                    {renderMarkdown(scientific_response.core_insight)}
                  </div>
                </div>
              )}
              {scientific_response.core_insight && (scientific_response.explanation || scientific_response.important_driver) && <hr className="border-neutral-800 my-1" />}
              {scientific_response.explanation && (
                <div className="mb-4 prose prose-sm prose-invert text-neutral-300">
                  <p className="text-xs font-semibold uppercase tracking-widest text-neutral-500 mb-1 mt-4">Explanation</p>
                  {renderMarkdown(scientific_response.explanation)}
                </div>
              )}
              {scientific_response.explanation && (scientific_response.important_driver || scientific_response.secondary_factors) && <hr className="border-neutral-800 my-1" />}
              {scientific_response.important_driver && (
                <div className="mb-4 prose prose-sm prose-invert text-neutral-300">
                  <p className="text-xs font-semibold uppercase tracking-widest text-neutral-500 mb-1 mt-4">Most Important Driver</p>
                  {renderMarkdown(scientific_response.important_driver)}
                </div>
              )}
              {scientific_response.important_driver && (scientific_response.secondary_factors || scientific_response.why_matters) && <hr className="border-neutral-800 my-1" />}
              {scientific_response.secondary_factors && (
                <div className="mb-4 prose prose-sm prose-invert text-neutral-300">
                  <p className="text-xs font-semibold uppercase tracking-widest text-neutral-500 mb-1 mt-4">Secondary Factors</p>
                  {Array.isArray(scientific_response.secondary_factors)
                    ? <ul className="list-disc pl-4 space-y-1">{scientific_response.secondary_factors.map((f, i) => (
                        <li key={i} className="text-neutral-300 text-sm">{f}</li>
                      ))}</ul>
                    : renderMarkdown(scientific_response.secondary_factors)}
                </div>
              )}
              {scientific_response.secondary_factors && (scientific_response.why_matters || scientific_response.nuance_exceptions) && <hr className="border-neutral-800 my-1" />}
              {scientific_response.why_matters && (
                <div className="mb-4 prose prose-sm prose-invert text-neutral-300">
                  <p className="text-xs font-semibold uppercase tracking-widest text-neutral-500 mb-1 mt-4">Why This Matters</p>
                  {renderMarkdown(scientific_response.why_matters)}
                </div>
              )}
              {scientific_response.why_matters && scientific_response.nuance_exceptions && <hr className="border-neutral-800 my-1" />}
              {scientific_response.nuance_exceptions && (
                <div className="mb-4 prose prose-sm prose-invert text-neutral-300">
                  <p className="text-xs font-semibold uppercase tracking-widest text-neutral-500 mb-1 mt-4">Nuance & Exceptions</p>
                  {renderMarkdown(scientific_response.nuance_exceptions)}
                </div>
              )}
            </div>
          )}

          {scientific_response.causal_chain && scientific_response.causal_chain.length > 0 && (
            <div className="mt-6">
              <p className="text-xs font-semibold uppercase tracking-widest text-neutral-500 mb-3 mt-4">
                Causal chain
              </p>
              <ol className="list-decimal pl-6 space-y-2 text-sm sm:text-base text-neutral-300">
                {scientific_response.causal_chain.map((step, i) => {
                  let content = null;
                  if (typeof step === 'string') {
                    content = step;
                  } else if (typeof step === 'object' && step !== null) {
                    if (step.cause && step.effect) {
                      content = (
                        <span>
                          <strong className="text-neutral-300">{step.cause}</strong> 
                          <span className="text-neutral-500 mx-1">→</span> 
                          <span>{step.effect}</span>
                        </span>
                      );
                    } else {
                      content = JSON.stringify(step);
                    }
                  } else {
                    content = String(step);
                  }
                  
                  return <li key={i}>{content}</li>;
                })}
              </ol>
            </div>
          )}
          
          {isLowConfidence && !pipeline_failure && (
             <p className="text-xs text-neutral-500 mt-4 pt-3 border-t border-neutral-800">
               Evidence grounding: inferred — not directly cited from retrieval
             </p>
          )}
        </div>
      )}

      {/* --- Nutritional Section --- */}
      {nutritional_response && (
        <div className="nutritional-section bg-orange-950/20 p-4 sm:p-5 rounded-xl border border-orange-900/30">
          <h2 className="text-xl sm:text-2xl font-serif text-orange-200 mb-4 pb-2 border-b border-orange-900/50 flex items-center gap-2">
            <span>🥚</span> Macronutrients
          </h2>

          <div className="prose prose-sm prose-invert text-neutral-300 mb-4 text-orange-100/90 whitespace-pre-line">
             {/* Clean up any backend bleed-through */}
             {renderMarkdown(nutritional_response.answer?.replace(/⚠️ \[RAG_FAILED_NO_CHUNKS\]\s*/g, ''))}
          </div>

          {/* Hidden Reasoning block */}
          {nutritional_response.agentic_reasoning && (
            <details className="mt-4 border border-orange-900/20 rounded-md bg-black/20 overflow-hidden group">
              <summary className="cursor-pointer text-xs font-mono text-orange-500/70 uppercase tracking-wider p-3 bg-black/40 hover:bg-black/60 transition-colors select-none">
                Show Reasoning
              </summary>
              <div className="p-4 prose prose-xs dark:prose-invert max-w-none text-neutral-400">
                {renderMarkdown(nutritional_response.agentic_reasoning)}
              </div>
            </details>
          )}

        </div>
      )}
  );
});

export default ResponseFormatter;

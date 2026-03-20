import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function stripMarkdownJson(text) {
  if (!text) return "";
  let clean = text.trim();
  if (clean.startsWith("```json")) clean = clean.substring(7);
  else if (clean.startsWith("```")) clean = clean.substring(3);
  if (clean.endsWith("```")) clean = clean.substring(0, clean.length - 3);
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

const ResponseFormatter = ({ text, isStreaming }) => {
  if (!text) return null;

  console.log("RAW TEXT:", text);

  // STEP 1: Streaming + JSON Parse Safety
  if (isStreaming || !isCompleteJSON(text)) {
    return (
      <div className="prose prose-sm prose-invert text-neutral-300 animate-fade-in">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      </div> // Fallback when incomplete
    );
  }

  // STEP 2: Safe parsing
  let data;
  try {
    const cleanJson = stripMarkdownJson(text);
    data = JSON.parse(cleanJson);
    console.log("PARSED JSON:", data);
  } catch (e) {
    console.log("JSON PARSE FAILED");
    // Failsafe: if looks complete but fails to parse
    return (
      <div className="prose prose-sm prose-invert text-neutral-300">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      </div> 
    );
  }

  const { scientific_response, nutritional_response, confidence, pipeline_failure, epistemic_state } = data;

  // TASK 7: FAIL-SAFE
  if (!scientific_response && !nutritional_response) {
    console.log("FAIL-SAFE: No structured responses found, falling back to markdown");
    return (
      <div className="prose prose-sm prose-invert text-neutral-300 animate-fade-in">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      </div> 
    );
  }

  const isLowConfidence = confidence !== undefined && confidence < 0.6;

  return (
    <div className="nutri-structured-response flex flex-col gap-6 w-full animate-fade-in">
      
      {/* --- Low Evidence Warning --- */}
      {isLowConfidence && !pipeline_failure && (
        <div className="flex items-center gap-2 p-3 bg-red-950/40 border border-red-900/50 rounded-lg text-red-400 text-sm font-medium">
          <span className="text-xl">⚠️</span> Low Evidence: This explanation relies on inferred heuristics rather than direct retrieval.
        </div>
      )}

      {/* --- Pipeline Failure / Epistemic State Banner --- */}
      {(pipeline_failure || (epistemic_state && epistemic_state !== "RESOLVED")) && (
        <div className={`flex flex-col gap-1 p-3 border rounded-lg text-sm ${
          epistemic_state === 'CONTRADICTED' ? 'bg-red-950/40 border-red-900/50 text-red-400' :
          epistemic_state === 'INSUFFICIENT_EVIDENCE' ? 'bg-amber-950/40 border-amber-900/50 text-amber-400' :
          'bg-blue-950/40 border-blue-900/50 text-blue-300'
        }`}>
          <div className="flex items-center gap-2 font-bold uppercase tracking-wider text-[10px]">
             <span>🔍</span> Pipeline State: {epistemic_state || "UNCERTAIN"}
          </div>
          <div className="opacity-90">
            {pipeline_failure ? "Reasoning pipeline was unable to reach high-confidence consensus." : "System operating at reduced epistemic certainty."}
          </div>
        </div>
      )}

      {/* --- Scientific Section --- */}
      {scientific_response && (
        <div className="scientific-section bg-neutral-900/40 p-4 sm:p-5 rounded-xl border border-neutral-800">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-2 border-b border-neutral-700/50">
            <h2 className="text-xl sm:text-2xl font-serif text-neutral-200 m-0 flex items-center gap-2">
              <span>🧪</span> Scientific Explanation
            </h2>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-mono font-medium border border-neutral-700/50 whitespace-nowrap self-start sm:self-auto ${
              scientific_response.mechanistic_grounding === 'RESOLVED' ? 'bg-green-900/20 text-green-400' : 
              'bg-neutral-800 text-neutral-400'
            }`}>
              {scientific_response.mechanistic_grounding || "Mechanistic Model"}
            </span>
          </div>
          
          {renderScientificNarrative(scientific_response.narrative)}

          {scientific_response.causal_chain && scientific_response.causal_chain.length > 0 && (
            <div className="mt-6">
              <h3 className="text-md sm:text-lg font-bold mb-3 text-blue-400 dark:text-blue-300">
                Causal chain
              </h3>
              <ol className="list-decimal pl-6 space-y-2 text-sm sm:text-base text-neutral-300">
                {scientific_response.causal_chain.map((step, i) => {
                  let content = null;
                  if (typeof step === 'string') {
                    content = step;
                  } else if (typeof step === 'object' && step !== null) {
                    if (step.cause && step.effect) {
                      content = (
                        <span>
                          <strong className="text-blue-300 dark:text-blue-200">{step.cause}</strong> 
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
    </div>
  );
};

export default ResponseFormatter;

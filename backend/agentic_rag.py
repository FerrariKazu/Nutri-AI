#!/usr/bin/env python3
"""
Agentic RAG with Chemical Reasoning

ReAct-style agent that autonomously:
1. Decides which databases to query
2. Queries PubChem API for molecular data
3. Reasons about food/recipe questions at chemical level
4. Provides scientifically accurate, chemically-grounded answers

This transforms the RAG system from a recipe collector into a food scientist!
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

# Add current and parent to path for flexible execution
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
if str(parent_dir) not in sys.path:
    sys.path.insert(1, str(parent_dir))

from tools.database_tools import DatabaseTools
from backend.llm.factory import LLMFactory
from utils.logging_config import setup_logging, get_logger
from utils.error_handling import retry_with_backoff, ErrorMessageFormatter
from utils.context_optimizer import ContextOptimizer
from prompt_logic.prompt_templates import PromptBuilder
from utils.response_formatter import ResponseFormatter

# Setup logging
setup_logging()
logger = get_logger(__name__)


class AgenticRAG:
    """
    ReAct-style agentic RAG system with chemical reasoning
    
    Uses iterative Thought → Action → Observation loop to:
    - Query multiple databases autonomously
    - Integrate PubChem API for molecular data
    - Provide chemically-grounded explanations
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        embedding_model: str = "BAAI/bge-m3",
        max_iterations: int = 3,  # Optimized for speed (down from 6)
    ):
        """
        Initialize agentic RAG system with all advanced features
        
        Args:
            max_iterations: Max tool calls before forcing final answer (default: 3)
            model_name: Optional model override
            embedding_model: Embedding model to use for RAG
        """
        logger.info("🚀 Initializing Advanced Agentic RAG System")
        
        # Core components
        self.tools = DatabaseTools()
        self.max_iterations = max_iterations
        
        # 🟢 Enforce Registry Usage
        self.client = LLMFactory.create_client(agent_name="rag_agent", model_name=model_name)
        self.model = self.client.model_name
        
        self.tool_descriptions = self._build_tool_descriptions()
        
        # RAG Hard Proof Metadata
        self.embedding_model = embedding_model
        self.vector_store_name = "faiss_food_v1" # Canonical name for audit
        
        # Advanced components
        try:
            from utils.context_optimizer import ContextOptimizer
            self.context_optimizer = ContextOptimizer()
            logger.info("✅ Context optimizer loaded")
        except Exception as e:
            logger.warning(f"Context optimizer failed to load: {e}")
            self.context_optimizer = None
        
        self.prompt_builder = Path(__file__).parent / "prompt_logic/prompt_templates.py" # For audit tracking
        try:
            from prompt_logic.prompt_templates import PromptBuilder
            self.prompt_builder = PromptBuilder()
            logger.info("✅ Prompt builder loaded")
        except Exception as e:
            logger.error(f"Prompt builder failed: {e}")
            raise
        
        logger.info("✅ System ready!")
    
    def _build_tool_descriptions(self) -> str:
        """Build formatted description of available tools"""
        tools = self.tools.get_available_tools()
        
        descriptions = ["AVAILABLE TOOLS:", "=" * 60]
        
        for tool in tools:
            descriptions.append(f"\n**{tool['name']}** (Priority: {tool['priority']})")
            descriptions.append(f"   {tool['description']}")
            descriptions.append(f"   Parameters: {tool['parameters']}")
        
        descriptions.append("\n" + "=" * 60)
        
        return "\n".join(descriptions)
    
    def _build_react_prompt(self, user_query: str, history: List[Dict]) -> List[Dict]:
        """
        Build ReAct-style prompt using advanced prompt builder.
        Returns a list of messages for client.chat()
        
        Args:
            user_query: User's question
            history: List of previous thought/action/observation dicts
            
        Returns:
            List of message dicts [{"role":..., "content":...}, ...]
        """
        
        # Detect query type and build specialized prompt
        query_type = self.prompt_builder.detect_query_type(user_query)
        logger.info(f"Query type detected: {query_type}")
        
        system_instruction = self.prompt_builder.build_prompt(
            query_type=query_type,
            tools_description=self.tool_descriptions,
            max_iterations=self.max_iterations
        )
        
        # Build history
        history_str = ""
        for i, entry in enumerate(history, 1):
            history_str += f"\n{'=' * 60}\n"
            history_str += f"Iteration {i}:\n"
            if 'thought' in entry:
                history_str += f"Thought: {entry['thought']}\n"
            if 'action' in entry:
                history_str += f"Action: {entry['action']}\n"
            if 'observation' in entry:
                history_str += f"Observation: {entry['observation']}\n"
        
        # Update iteration count in system prompt
        system_instruction = system_instruction.replace('{iteration}', str(len(history) + 1))
        
        # User prompt
        user_content = f"""USER QUERY: {user_query}
{history_str}

Continue your reasoning. Remember to use the ReAct format:
Thought: [your reasoning]
Action: tool_name(parameter="value")

Or if you have enough information:
Thought: I have sufficient information
Final Answer: [your answer]
"""
        
        return [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_content}
        ]
    
    def _parse_response(self, response: str) -> Dict[str, str]:
        """
        Parse LLM response to extract Thought, Action, or Final Answer
        
        Returns:
            Dict with 'thought', 'action', and/or 'final_answer' keys
        """
        result = {}
        
        # Extract Thought
        thought_match = re.search(r'Thought:\s*(.*?)(?=\n(?:Action:|Final Answer:)|$)', response, re.DOTALL | re.IGNORECASE)
        if thought_match:
            result['thought'] = thought_match.group(1).strip()
        
        # Extract Action
        action_match = re.search(r'Action:\s*(.*?)(?=\n(?:Thought:|Observation:|Final Answer:)|$)', response, re.DOTALL | re.IGNORECASE)
        if action_match:
            result['action'] = action_match.group(1).strip()
        
        # Extract Final Answer
        final_match = re.search(r'Final Answer:\s*(.*)', response, re.DOTALL | re.IGNORECASE)
        if final_match:
            result['final_answer'] = final_match.group(1).strip()
        
        return result
    
    def _execute_action(self, action_str: str) -> str:
        """
        Execute a tool action
        
        Args:
            action_str: Tool call string like 'search_pubchem_compound(compound_name="curcumin")'
            
        Returns:
            Tool output string
        """
        try:
            # Parse tool name and parameters
            match = re.match(r'(\w+)\((.*)\)', action_str)
            if not match:
                return f"Error: Invalid action format. Use tool_name(param=\"value\")"
            
            tool_name = match.group(1)
            params_str = match.group(2)
            
            # Parse parameters (simple parser for key="value" format)
            params = {}
            for param_match in re.finditer(r'(\w+)=["\']([^"\']+)["\']', params_str):
                params[param_match.group(1)] = param_match.group(2)
            
            # Convert top_k to int if present
            if 'top_k' in params:
                params['top_k'] = int(params['top_k'])
            if 'limit' in params:
                params['limit'] = int(params['limit'])
            
            # Execute tool
            if hasattr(self.tools, tool_name):
                tool_method = getattr(self.tools, tool_name)
                result = tool_method(**params)
                
                # 🟢 PHASE 3: RAG Alignment & PubChem Precedence
                # If this is a search tool, verify results
                if "search" in tool_name and "pubchem" not in tool_name:
                    result = self._align_rag_result(tool_name, params.get("query", ""), result)
                
                # 🟢 RAG Hard Proof Logging
                logger.info(f"[RAG_PROOF] Tool: {tool_name} | Params: {params} | Results: {len(result) if isinstance(result, list) else 'text'}")
                if "search" in tool_name and not result:
                     logger.warning(f"[RAG_PROOF] ⚠️ Zero chunks retrieved from {tool_name}")
                
                return result
            else:
                return f"Error: Unknown tool '{tool_name}'. Available tools: {', '.join([t['name'] for t in self.tools.get_available_tools()])}"
                
        except Exception as e:
            return f"Error executing action: {str(e)}"
    
    def _align_rag_result(self, tool_name: str, query: str, result: str) -> str:
        """
        Enforce PubChem precedence and filter unverified nutrition claims.
        Logs [RAG_CONFLICT] if RAG contradicts PubChem.
        """
        # If the result suggests nutrition/chemical facts, cross-verify
        chemical_terms = ["formula", "molecular", "mg", "ug", "acid", "compound", "vitamin"]
        if any(term in result.lower() for term in chemical_terms):
            logger.info(f"[RAG_ALIGN] Nutrition/Chemical info detected in {tool_name} results. cross-verifying...")
            
            # Simple heuristic: if query looks like a compound, try PubChem
            if len(query.split()) <= 2:
                from backend.pubchem_client import PubChemClient, PubChemNotFound
                client = PubChemClient()
                
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                try:
                    cid = loop.run_until_complete(client.search_compound(query))
                    props = loop.run_until_complete(client.get_compound_properties(cid))
                    
                    # Log successful cross-verification
                    logger.info(f"[RAG_ALIGN] CID {cid} found for '{query}'. Verifying RAG consistency.")
                    
                    formula = props.get("MolecularFormula", "")
                    weight = props.get("MolecularWeight", "")
                    
                    # Prepend PubChem truth
                    truth = f"✅ [PUBCHEM_VERIFIED] {query} (CID:{cid}): Formula={formula}, MW={weight}"
                    
                    # 🔬 CONFLICT DETECTION
                    if formula:
                        # Regex to find things that look like formulas in the RAG result
                        rag_formulas = re.findall(r'\b[A-Z][a-z]?\d*[A-Z][a-z]?\d*\b', result)
                        for rf in rag_formulas:
                            if rf != formula and len(rf) > 2:
                                logger.warning(f"[RAG_CONFLICT] Contradiction! RAG says {rf}, PubChem says {formula}")
                                return f"❌ [RAG_CONFLICT] RAG result for '{query}' contradicts PubChem truth ({formula} vs {rf}).\nTRUSTED DATA: {truth}\n\n[UNTRUSTED RAG CONTEXT]\n{result}"

                    return f"{truth}\n\n[RAG_CONTEXT]\n{result}"

                except (PubChemNotFound, Exception) as e:
                    logger.warning(f"[RAG_ALIGN] PubChem verify failed for '{query}': {e}")
                    # Filter unverified nutrition claims
                    if "usda" in tool_name or "open_nutrition" in tool_name:
                         return f"⚠️ [UNVERIFIED_DATA] No PubChem CID found for this claim.\n{result}"
                finally:
                    loop.run_until_complete(client.close())
        
        return result

    def stream_query(self, user_query: str):
        """
        Simplified streaming query with reduced complexity and better error handling.
        
        Uses a single LLM call with comprehensive prompt to reduce failure points.
        
        Yields:
            Dict events: 'type' (thinking, token, error) and 'content'/'stage'
        """
        history = []
        
        # Single comprehensive prompt approach
        yield {"type": "thinking", "stage": "start", "content": "🧠 Analyzing your request..."}
        
        try:
            # Build comprehensive prompt with all context
            messages = self._build_react_prompt(user_query, history)
            
            yield {"type": "thinking", "stage": "reasoning", "content": "🤔 Generating response..."}
            
            # 🟢 Use unified client stream
            stream = self.client.stream_text(
                messages=messages,
                temperature=0.3
            )
            
            buffer = ""
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    token = chunk['message']['content']
                    buffer += token
                    
                    # Apply real-time cleaning to prevent leakage
                    cleaned_token = self._clean_streaming_token(token, buffer)
                    if cleaned_token:
                        yield {"type": "token", "content": cleaned_token}
        
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {"type": "error", "content": f"LLM Error: {str(e)}"}
    
    def _clean_streaming_token(self, token: str, buffer: str) -> str:
        """
        Real-time response cleaning during streaming to prevent system prompt leakage.
        
        Args:
            token: Current token being processed
            buffer: Full response buffer so far
            
        Returns:
            Cleaned token or empty string if should be filtered
        """
        if not token:
            return ""
        
        # Check if we're still in system content
        system_indicators = [
            "I am NUTRI-CHEM GPT",
            "My capabilities include",
            "Would you like to begin?",
            "System Prompt:",
            "CRITICAL OUTPUT INSTRUCTION:"
        ]
        
        for indicator in system_indicators:
            if indicator in buffer:
                # If we find system content, skip until we find Final Answer
                if "Final Answer:" in buffer:
                    # Extract only the final answer part
                    parts = buffer.split("Final Answer:", 1)
                    if len(parts) > 1:
                        final_part = parts[1]
                        # Return only new content from final answer
                        if len(final_part) > len(getattr(self, '_last_final_answer_length', 0)):
                            new_content = final_part[getattr(self, '_last_final_answer_length', 0):]
                            self._last_final_answer_length = len(final_part)
                            return new_content
                return ""
        
        # Filter out thinking blocks in real-time
        if re.search(r'<[/]?think>', token, re.IGNORECASE):
            return ""
        
        # Filter out ReAct artifacts
        if re.search(r'^(Thought:|Action:|Observation:)', token.strip()):
            return ""
        
        return token

    def _separate_reasoning_from_answer(self, full_response: str) -> Dict:
        """
        Separate agent's reasoning process from final answer
        
        Returns:
            (final_answer, reasoning_steps)
        """
        reasoning_steps = []
        final_answer = ""
        
        # Split response into sections
        sections = full_response.split('\n')
        
        current_step = {}
        in_final_answer = False
        
        for line in sections:
            line_stripped = line.strip()
            
            # Check for reasoning markers
            if line_stripped.startswith('Thought:'):
                if current_step:
                    reasoning_steps.append(current_step)
                current_step = {
                    'type': 'thought',
                    'content': line_stripped.replace('Thought:', '').strip()
                }
            
            elif line_stripped.startswith('Action:'):
                if current_step:
                    reasoning_steps.append(current_step)
                current_step = {
                    'type': 'action',
                    'content': line_stripped.replace('Action:', '').strip()
                }
            
            elif line_stripped.startswith('Observation:'):
                if current_step:
                    reasoning_steps.append(current_step)
                current_step = {
                    'type': 'observation',
                    'content': line_stripped.replace('Observation:', '').strip()
                }
            
            elif line_stripped.startswith('Final Answer:') or in_final_answer:
                # Start capturing final answer
                if not in_final_answer:
                    in_final_answer = True
                    if current_step:
                        reasoning_steps.append(current_step)
                        current_step = {}
                    # Don't include "Final Answer:" label
                    line_stripped = line_stripped.replace('Final Answer:', '').strip()
                
                if line_stripped:  # Don't add empty lines
                    final_answer += line_stripped + '\n'
            
            elif current_step and not in_final_answer:
                # Continue current step content
                current_step['content'] += '\n' + line_stripped
        
        # Add last step if exists
        if current_step:
            reasoning_steps.append(current_step)
        
        return final_answer.strip(), reasoning_steps

    def extract_only_answer(self, text: str) -> str:
        """
        Extract ONLY the final answer, remove everything else (Nuclear Option)
        """
        if not text:
            return ""
            
        # Remove system prompt if present
        if "I am NUTRI-CHEM GPT" in text:
            parts = text.split("Would you like to begin?")
            if len(parts) > 1:
                text = parts[1]
        
        # Remove thinking tags
        text = re.sub(r'<[/]?think>.*?</?think>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'</?thinking>.*?</thinking>', '', text, flags=re.DOTALL)
        
        # Remove Thought/Action/Observation sections
        # Also remove "System Prompt:" leaks
        text = re.sub(r'System Prompt:.*?(?=\n|$)', '', text)
        
        # Extract Final Answer section if present
        if "Final Answer:" in text:
            text = text.split("Final Answer:")[-1]
        
        # Filter out line-by-line artifacts
        lines = text.split('\n')
        filtered = []
        skip_line = False
        
        for line in lines:
            stripped = line.strip()
            # aggressive filtering of ReAct artifacts
            if any(stripped.startswith(x) for x in ['Thought:', 'Action:', 'Observation:', 'System:', 'I am NUTRI-CHEM']):
                continue
                
            filtered.append(line)
        
        return '\n'.join(filtered).strip()

    def query(self, user_query: str, mode: str = None) -> Dict:
        """
        Process query and return structured response
        
        Returns:
        {
            'answer': 'Final answer text',
            'reasoning': [list of reasoning steps],
            'metadata': { ... }
        }
        """
        import time
        start_time = time.time()
        
        logger.info(f"\n{'=' * 60}")
        logger.info(f"USER QUERY: {user_query}")
        logger.info(f"{'=' * 60}\n")
        
        # We will use the stream_query logic to execute the ReAct loop
        # collecting the output into a structured format
        
        reasoning_steps = []
        final_answer = ""
        tools_used = set()
        
        # Execute query using streaming logic but capture events
        for event in self.stream_query(user_query):
            if event['type'] == 'thinking':
                # Map thinking stages to reasoning steps if possible
                # But stream_query yields simplified thinking messages.
                # To get detailed reasoning, we might need to modify stream_query or parse logs?
                # Actually, stream_query logs 'Thought' and 'Action'.
                # Let's use the provided plan's approach: generate response and separate it.
                pass
            elif event['type'] == 'token':
                final_answer += event['content']
            elif event['type'] == 'error':
                 final_answer = f"Error: {event['content']}"

        # Wait, the user's plan uses `_generate_response_internal`.
        # But `stream_query` implements the loop.
        # If I rewrite `query` to use `_separate_reasoning_from_answer`, I need the FULL raw response including thoughts.
        # But `stream_query` returns tokens of the FINAL ANSWER only (after thoughts).
        
        # Solution: We need to capture the thoughts during execution.
        # Since I can't easily change `stream_query` to return raw text without breaking it, 
        # I will implement the loop in `query` similar to `stream_query` but collecting steps.
        
        history = []
        for iteration in range(self.max_iterations):
            # ... (Logic similar to stream_query but synchronous) ...
            # Actually, to save code duplication, I'll rely on `stream_query` logic
            # modifying it to return the history at the end?
            pass

        # RE-READING USER PLAN:
        # The user provided:
        # raw_response = self._generate_response_internal(user_query)
        # final_answer, reasoning_steps = self._separate_reasoning_from_answer(raw_response)
        
        # This implies `_generate_response_internal` returns the full LLM output (Thoughts + Output).
        # But `AgenticRAG` runs a ReAct LOOP. The "Full Response" is actually multiple LLM calls.
        
        # Adaptation: I will implement `query` to run the loop and accumulate reasoning.
        
        # Re-implementing logic for the `query` method to match user request:
        
        history = []
        prompt = self._build_react_prompt(user_query, history) # Initial prompt
        
        # We need to loop.
        # But this is complex to replace in one go.
        logger.info(f"Executing structured query for: {user_query[:50]}...")
        
        # 🟢 RAG Suppression Support
        if kwargs.get("rag_disabled", False):
            logger.info("[RAG_PROOF] RAG suppressed via flag")
            # Force a direct answer without tool loop
            messages = [{"role": "system", "content": "RAG IS DISABLED for this request. Answer using internal knowledge only."}, {"role": "user", "content": user_query}]
            llm_output = self.client.generate_text(messages=messages, max_new_tokens=2048)
            return {
                'answer': llm_output,
                'reasoning': [{'type': 'thought', 'content': 'RAG suppressed. Using internal knowledge.'}],
                'metadata': {'rag_active': False, 'chunks_retrieved': False, 'mode': mode or 'standard'}
            }
            
        reasoning_steps = []
        final_answer_text = ""
        
        for iteration in range(self.max_iterations):
            messages = self._build_react_prompt(user_query, history)
            
            try:
                llm_output = self.client.generate_text(
                    messages=messages,
                    temperature=0.7,
                    max_new_tokens=2048
                )
            except Exception as e:
                return {'answer': f"Error: {e}", 'reasoning': [], 'metadata': {}}
            
            # Parse
            parsed = self._parse_response(llm_output)
            
            if 'thought' in parsed:
                reasoning_steps.append({'type': 'thought', 'content': parsed['thought']})
            
            if 'action' in parsed:
                action = parsed['action']
                reasoning_steps.append({'type': 'action', 'content': action})
                
                # Extract tool name
                tool_match = re.match(r'(\w+)\(', action)
                if tool_match:
                    tools_used.add(tool_match.group(1))
                
                # Execute
                observation = self._execute_action(action)
                reasoning_steps.append({'type': 'observation', 'content': observation})
                
                history.append({'thought': parsed.get('thought'), 'action': action, 'observation': observation})
            if 'final_answer' in parsed:
                final_answer_text = parsed['final_answer']
                break
        
        # If no final answer after loop
        if not final_answer_text:
             # Force final answer logic
             final_prompt = f"Based on: {user_query} and history: {json.dumps(history)}, provide final answer."
             try:
                 final_answer_text = self.client.generate_text(
                     messages=[{"role": "user", "content": final_prompt}],
                     max_new_tokens=512
                 )
             except:
                 final_answer_text = "Error generating final answer."

        # 🟢 PHASE 3: Enforce RAG Contract
        rag_active = any("[RAG_PROOF]" in str(it) for it in reasoning_steps)
        chunks_found = any("Results: [1-9]" in str(it) for it in reasoning_steps) # Naive check for count > 0
        
        # [NEW] Nutrition Claim Auto-Labeling (PHASE 3 Intelligence Hardening)
        # Any response from RAG containing nutrition claims is marked as supporting but not verified.
        nutrition_keywords = ["fiber", "protein", "vitamin", "iron", "calcium", "nutrient", "nutrition"]
        has_nutrition_claim = any(kw in final_answer_text.lower() for kw in nutrition_keywords)
        
        metadata = {
            "rag_active": rag_active,
            "chunks_retrieved": chunks_found,
            "agent_iterations": len(reasoning_steps),
            "nutrition_supported_by_rag": has_nutrition_claim
        }
        
        if not chunks_found and not kwargs.get("rag_disabled", False):
            metadata["rag_status"] = "FAILED_NO_CHUNKS"
            final_answer_text = f"⚠️ [RAG_FAILED_NO_CHUNKS] {final_answer_text}"
        
        # If it has nutrition claims but ONLY comes from RAG (no hard PubChem/USDA in this context yet)
        # the ClaimVerifier will handle the final status, but we tag it here for tracing.
        if has_nutrition_claim and rag_active:
            logger.info("[RAG_TRACE] Nutrition claim detected in RAG output - tagging for verifier downgrading.")

        # Format Final Answer
        from backend.utils.markdown_formatter import MarkdownFormatter
        # NUCLEAR CLEANING
        final_answer_text = self.extract_only_answer(final_answer_text)
        final_answer_text = MarkdownFormatter.format_for_gradio(final_answer_text)
        
        # Update metadata with original values and new RAG status
        metadata.update({
            'mode': mode or 'standard',
            'tools_used': list(tools_used),
            'time_taken': time.time() - start_time,
            'num_reasoning_steps': len(reasoning_steps)
        })

        return {
            'answer': final_answer_text,
            'reasoning': reasoning_steps,
            'metadata': {
                'mode': mode or 'standard',
                'tools_used': list(tools_used),
                'time_taken': time.time() - start_time,
                'num_reasoning_steps': len(reasoning_steps)
            }
        }


if __name__ == "__main__":
    # Quick test
    print("Testing Agentic RAG...")
    
    agent = AgenticRAG(max_iterations=4)
    
    # Test query
    query = "Why is turmeric anti-inflammatory? Explain the molecular mechanism."
    
    print(f"\nQuery: {query}\n")
    answer = agent.query(query)
    
    print(f"\n{'=' * 60}")
    print("FINAL ANSWER:")
    print(answer)
    print('=' * 60)

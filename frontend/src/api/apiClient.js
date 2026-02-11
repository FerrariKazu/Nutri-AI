/**
 * Pure JavaScript API Client
 * NO REACT - Just plain imperative functions
 * Handles all networking, streaming, errors, retries
 */

import { getUserId } from '../utils/memoryManager';

// ============================================================================ 
// CONFIGURATION
// ============================================================================ 

let _performanceMode = false;

const LOCAL_BACKEND_URLS = [
    'http://localhost:8000',
    'http://localhost:8001',
];

// Fallback if local backend isn't running
const RAILWAY_BACKEND_URL = 'https://nutri-ai.up.railway.app';

// ============================================================================ 
// EXTREME DEBUG LOGGING - NEVER SUPPRESS
// ============================================================================ 
const DEBUG_MODE = true;

function debugLog(category, message, data = null) {
    if (!DEBUG_MODE) return;
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [${category}]`;

    if (data) {
        console.log(`${prefix} ${message}`, data);
    } else {
        console.log(`${prefix} ${message}`);
    }
}

function debugError(category, message, error = null) {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [${category}] ❌`;

    console.error(`${prefix} ${message}`);
    if (error) {
        console.error(`${prefix} Error details:`, {
            name: error.name,
            message: error.message,
            status: error.status,
            response: error.response,
            stack: error.stack
        });
    }
}

let finalBackendURL = '';

async function detectBackend() {
    debugLog('BACKEND', '🔍 Starting backend detection...');

    // 0. Environment Guard: If we are in production, FORCE relative URLs to use Vercel Proxy.
    // This overrides any VITE_API_URL that might be set in the environment.
    if (import.meta.env.PROD) {
        debugLog('BACKEND', '🚀 Production detected. Forcing relative URLs for same-origin proxying.');
        return '';
    }

    // 1. Explicit VITE_API_URL (Local Development only or if explicitly needed)
    if (import.meta.env.VITE_API_URL) {
        const envUrl = import.meta.env.VITE_API_URL.replace(/\/$/, '');
        // Only allow if it's localhost (local development)
        if (envUrl.includes('localhost') || envUrl.includes('127.0.0.1')) {
            debugLog('BACKEND', `🌍 Using Local VITE_API_URL: ${envUrl}`);
            return envUrl;
        }
        debugLog('BACKEND', `🚫 Ignoring remote VITE_API_URL: ${envUrl} (Staying same-origin)`);
    }

    // 2. Localhost Proxy Guard
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        debugLog('BACKEND', '🛡️ Localhost detected. Using relative URL for Vite Proxy.');
        return '';
    }

    // 1. Try local URLs first
    for (const url of LOCAL_BACKEND_URLS) {
        try {
            debugLog('BACKEND', `   Trying: ${url}`);
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2000); // 2s timeout
            const response = await fetch(`${url}/health`, {
                signal: controller.signal,
                headers: { 'ngrok-skip-browser-warning': 'true' }
            });
            clearTimeout(timeoutId);
            if (response.ok) {
                const healthData = await response.json().catch(() => ({}));
                if (healthData.status === 'constrained') {
                    _performanceMode = true;
                    debugLog('BACKEND', '⚠️ Performance Mode active (Resource Constrained)');
                }
                debugLog('BACKEND', `✅ Backend found at: ${url}`);
                console.log(`✅ Local Backend detected, using: ${url}`);
                return url;
            }

        } catch (error) {
            debugLog('BACKEND', `   ❌ ${url} - ${error.message || 'not reachable'}`);
        }
    }

    // 2. Final Fallback: Same-Origin (Relative Paths)
    // This allows Vercel (Production) or Vite Proxy (Local) to handle the forwarding.
    debugLog('BACKEND', '📡 Final Fallback: Using relative URL (Same-Origin Proxy Mode)');
    return '';
}

// Cached backend URL promise
let backendUrlPromise = null;

function getBackendURL() {
    if (!backendUrlPromise) {
        backendUrlPromise = detectBackend().then(url => {
            console.log(`📡 [API] Final Backend URL selected: "${url}" ${url === '' ? '(Using Vite Proxy)' : ''}`);
            return url;
        });
    }
    return backendUrlPromise;
}

export function getPerformanceMode() {
    return _performanceMode;
}



const API_CONFIG = {
    timeout: 120000,  // 120 seconds for LLM workloads
    maxRetries: 3,
    retryDelay: 1000,  // 1 second
};

// ============================================================================ 
// ERROR HANDLING
// ============================================================================ 

class APIError extends Error {
    constructor(message, status, response) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.response = response;
    }
}

class NetworkError extends Error {
    constructor(message) {
        super(message);
        this.name = 'NetworkError';
    }
}

class TimeoutError extends Error {
    constructor(message) {
        super(message);
        this.name = 'TimeoutError';
    }
}

// ============================================================================ 
// UTILITY FUNCTIONS
// ============================================================================ 

/**
 * Create AbortController with timeout
 */
function createTimeoutController(timeoutMs) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    // Cleanup function
    const cleanup = () => clearTimeout(timeoutId);

    return { controller, cleanup };
}

/**
 * Retry with exponential backoff
 */
async function retry(fn, maxRetries, baseDelay) {
    let lastError;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
            return await fn();
        } catch (error) {
            lastError = error;

            // Don't retry on client errors (4xx)
            if (error instanceof APIError && error.status >= 400 && error.status < 500) {
                throw error;
            }

            // Don't retry on user abort
            if (error.name === 'AbortError') {
                throw error;
            }

            // Wait before retrying (exponential backoff)
            if (attempt < maxRetries - 1) {
                const delay = baseDelay * Math.pow(2, attempt);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }

    throw lastError;
}

/**
 * Parse JSON safely
 */
/**
 * Parse JSON safely without crashing
 */
function safeParseJSON(text) {
    if (!text || typeof text !== 'string') return null;
    try {
        return JSON.parse(text);
    } catch (e) {
        return null;
    }
}

/**
 * Get or generate a persistent session ID
 */
export function getSessionId() {
    let sessionId = localStorage.getItem('nutri_session_id');
    if (!sessionId) {
        sessionId = `sess_${Math.random().toString(36).substring(2, 11)}_${Date.now()}`;
        localStorage.setItem('nutri_session_id', sessionId);
    }
    return sessionId;
}

/**
 * Clear current session
 */
export function clearSession() {
    localStorage.removeItem('nutri_session_id');
}


// ============================================================================ 
// CORE API FUNCTIONS
// ============================================================================ 

/**
 * Send a simple prompt and get complete response
 * 
 * @param {string} prompt - User's message
 * @param {string} mode - 'simple' | 'standard' | 'chemistry'
 * @param {AbortSignal} signal - Optional abort signal
 * @returns {Promise<Object>} - { answer, reasoning, metadata }
 */
export async function sendPrompt(prompt, mode = 'standard', signal = null) {
    const { controller, cleanup } = createTimeoutController(API_CONFIG.timeout);
    const baseURL = await getBackendURL();

    // ========== EXTREME DEBUG: REQUEST START ==========
    debugLog('API', '='.repeat(50));
    debugLog('API', `📤 SENDING REQUEST: POST ${baseURL}/api/chat`);
    debugLog('API', `   Mode: ${mode}`);
    debugLog('API', `   Prompt: ${prompt.substring(0, 100)}...`);
    debugLog('API', '='.repeat(50));

    try {
        const response = await retry(async () => {
            const res = await fetch(`${baseURL}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'ngrok-skip-browser-warning': 'true',
                    'Bypass-Tunnel-Reminder': 'true',
                    'X-User-Id': getUserId(),
                },
                body: JSON.stringify({
                    message: prompt,
                    mode: mode,
                }),
                signal: signal || controller.signal,
            });

            // Handle HTTP errors
            if (!res.ok) {
                const errorText = await res.text();
                const errorData = safeParseJSON(errorText);

                debugError('API', `HTTP ERROR: ${res.status} ${res.statusText}`, {
                    status: res.status,
                    response: errorData,
                    rawText: errorText
                });

                throw new APIError(
                    errorData?.error || `HTTP ${res.status}: ${res.statusText}`,
                    res.status,
                    errorData
                );
            }

            debugLog('API', `📥 RESPONSE: ${res.status} OK`);
            return res;
        }, API_CONFIG.maxRetries, API_CONFIG.retryDelay);

        // Sanitize response to prevent system prompt leakage
        const sanitizeResponse = (data) => {
            const systemPhrases = [
                'I am NUTRI-CHEM GPT',
                'I am designed to provide',
                'My capabilities include',
                'Would you like to begin?',
                'Please specify your query'
            ];

            let content = data.answer || data.reply || '';
            let contentString = typeof content === 'string' ? content : JSON.stringify(content);

            // Check if response starts with system prompt
            if (systemPhrases.some(phrase => contentString.includes(phrase))) {
                console.warn('⚠️ Frontend filtered leaked system prompt');
                const delimiters = ['Would you like to begin?', 'Please specify your query'];

                for (const delim of delimiters) {
                    const parts = contentString.split(delim);
                    if (parts.length > 1) {
                        // Take the last part which is likely the actual Answer
                        content = parts[parts.length - 1].trim();
                        // Clean up leading punctuation often left behind
                        content = content.replace(/^["\?\.\s]+/, '');
                        break;
                    }
                }
            }

            return {
                ...data,
                answer: content,
                reply: content
            };
        };

        const jsonData = await response.json();
        debugLog('API', `📥 RESPONSE DATA:`, jsonData);
        return sanitizeResponse(jsonData);

    } catch (error) {
        // ========== EXTREME DEBUG: ERROR DETAILS ==========
        debugError('API', 'REQUEST FAILED', error);

        // Classify error
        if (error.name === 'AbortError') {
            throw new TimeoutError('Request timed out');
        }

        if (error instanceof APIError) {
            throw error;
        }

        // Network error
        throw new NetworkError(error.message || 'Network request failed');

    } finally {
        cleanup();
    }
}

/**
 * Stream a prompt response token by token
 * 
 * @param {string} prompt - User's message
 * @param {string} mode - Response mode
 * @param {Function} onToken - Callback for each token: (token) => void
 * @param {Function} onComplete - Callback when done: (fullResponse) => void
 * @param {Function} onError - Callback on error: (error) => void
 * @param {AbortSignal} signal - Optional abort signal
 * @returns {Function} - Cleanup/abort function
 */
export function streamPrompt(
    prompt,
    mode = 'standard',
    onToken,
    onComplete,
    onError,
    signal = null
) {
    let aborted = false;
    const { controller, cleanup } = createTimeoutController(API_CONFIG.timeout);

    // Combined abort signal
    const combinedSignal = signal || controller.signal;

    // ========== EXTREME DEBUG: STREAM START ==========
    debugLog('STREAM', '='.repeat(50));
    debugLog('STREAM', '🔄 STARTING STREAM REQUEST');
    debugLog('STREAM', `   Prompt: ${prompt.substring(0, 100)}...`);
    debugLog('STREAM', `   Mode: ${mode}`);
    debugLog('STREAM', '='.repeat(50));

    // NUCLEAR CLEAN RESPONSE FUNCTION
    const cleanResponse = (text) => {
        // Remove system prompt
        const systemPhrases = [
            'I am NUTRI-CHEM GPT', 'My capabilities include', 'Would you like to begin', 'Please specify your query'
        ];

        for (const phrase of systemPhrases) {
            if (text.includes(phrase)) {
                text = text.split(phrase).pop();
            }
        }

        // Remove thinking sections
        text = text.replace(/<\/?think>.*?<\/think>/gs, '');
        text = text.replace(/Thought:.*?(?=\n|$)/g, '');
        text = text.replace(/Action:.*?(?=\n|$)/g, '');
        text = text.replace(/Observation:.*?(?=\n|$)/g, '');

        // Extract Final Answer if present
        if (text.includes('Final Answer:')) {
            text = text.split('Final Answer:').pop();
        }

        // Remove leading punctuation
        return text.replace(/^["\s\.:\?]+/, '');
    };

    // Start streaming
    (async () => {
        try {
            const baseURL = await getBackendURL();
            debugLog('STREAM', `📡 Fetching from: ${baseURL}/api/chat/stream`);
            debugLog('STREAM', `📡 Fetching from: ${baseURL}/api/chat/stream`);
            const params = new URLSearchParams({
                message: prompt,
                mode: mode
            });
            const response = await fetch(`${baseURL}/api/chat/stream?${params.toString()}`, {
                method: 'GET',
                headers: {
                    'ngrok-skip-browser-warning': 'true',
                    'X-User-Id': getUserId(),
                },
                signal: combinedSignal,
            });

            if (!response.ok) {
                const errorText = await response.text();
                debugError('STREAM', `HTTP ERROR: ${response.status}`, {
                    status: response.status,
                    text: errorText
                });
                throw new APIError(
                    `HTTP ${response.status}: ${response.statusText}`,
                    response.status
                );
            }

            debugLog('STREAM', '🟢 Response OK, starting reader...');

            // Get reader from response body
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            let fullResponse = '';
            let buffer = '';
            let rawBuffer = ''; // To track raw stream for cleaning
            let previousCleanLength = 0;
            let tokenCount = 0;

            // Read stream
            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    debugLog('STREAM', '🏁 Reader done');
                    break;
                }
                if (aborted) {
                    debugLog('STREAM', '🛑 Stream aborted by user/timeout');
                    break;
                }

                // Decode chunk
                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;

                // Process complete lines (SSE format)
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // Keep incomplete line in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6); // Remove "data: " prefix

                        if (data === '[DONE]') {
                            debugLog('STREAM', '✅ [DONE] marker received');
                            break;
                        }

                        // SAFE PARSING: Only parse if it looks like JSON
                        const parsed = data.trim().startsWith('{') ? safeParseJSON(data) : null;
                        const type = parsed?.type || 'token';

                        if (type === 'status' || parsed?.message) {
                            // Inform UI of status change
                            onToken(parsed?.message || data, 'status');
                        } else if (type === 'ping') {
                            debugLog('STREAM', '💓 Ping received');
                        } else if (type === 'token' || type === 'content' || !parsed) {
                            const token = parsed?.content || parsed?.token || data || '';
                            if (token) {
                                tokenCount++;
                                rawBuffer += token;
                                const cleanBuffer = cleanResponse(rawBuffer);

                                if (cleanBuffer.length > previousCleanLength) {
                                    const newContent = cleanBuffer.slice(previousCleanLength);
                                    fullResponse += newContent;
                                    onToken(newContent, 'token');
                                    previousCleanLength = cleanBuffer.length;
                                }
                            }
                        } else if (type === 'error') {
                            throw new Error(parsed.message || 'Stream error');
                        }
                    }
                }
            }

            debugLog('STREAM', `✨ Stream complete. Total tokens emitted: ${tokenCount}`);

            // Call completion callback
            if (!aborted && onComplete) {
                onComplete(fullResponse);
            }

        } catch (error) {
            debugError('STREAM', 'FATAL ERROR in stream', error);
            if (!aborted && onError) {
                if (error.name === 'AbortError') {
                    onError(new TimeoutError('Stream timed out'));
                } else if (error instanceof APIError) {
                    onError(error);
                } else {
                    onError(new NetworkError(error.message));
                }
            }
        } finally {
            cleanup();
        }
    })();

    // Return abort function
    return () => {
        aborted = true;
        controller.abort();
    };
}

/**
 * Get system stats
 */
export async function getConversationsList() {
    debugLog('API', '🔄 Fetching conversation list...');
    try {
        const baseURL = await getBackendURL();
        const response = await fetch(`${baseURL}/api/conversations`, {
            headers: {
                'ngrok-skip-browser-warning': 'true',
                'X-User-Id': getUserId(),
            }
        });

        if (!response.ok) throw new Error(`Failed to fetch list: ${response.status}`);

        const data = await response.json();
        debugLog('API', `📥 Received ${data.conversations?.length || 0} conversations`);
        return data.conversations || [];
    } catch (error) {
        debugError('API', 'List fetch failed', error);
        return [];
    }
}

export async function createNewSession() {
    debugLog('API', '🆕 Creating new session...');
    try {
        const baseURL = await getBackendURL();
        const response = await fetch(`${baseURL}/api/conversation`, {
            method: 'POST',
            headers: {
                'ngrok-skip-browser-warning': 'true',
                'X-User-Id': getUserId(),
            }
        });

        if (!response.ok) throw new Error('Creation failed');

        const data = await response.json();

        // Update local storage
        localStorage.setItem('nutri_session_id', data.session_id);

        return data.session_id;
    } catch (error) {
        debugError('API', 'Create failed', error);
        // Fallback to random client-side ID
        return getSessionId();
    }
}

/**
 * Get the current canonical conversation memory from the backend.
 * Essential for UI hydration on page load.
 */
export async function getConversation(sessionId) {
    debugLog('API', `🔄 Fetching conversation history for session: ${sessionId}`);
    try {
        const baseURL = await getBackendURL();
        const response = await fetch(`${baseURL}/api/conversation?session_id=${sessionId}`, {
            headers: {
                'ngrok-skip-browser-warning': 'true',
                'X-User-Id': getUserId(),
            }
        });

        if (!response.ok) {
            throw new Error(`Failed to fetch history: ${response.status}`);
        }

        const data = await response.json();

        // [TRACE_AUDIT] Step 8: Hydration validation
        const lastMsg = data.messages?.[data.messages.length - 1];
        if (lastMsg?.executionTrace) {
            const claims = lastMsg.executionTrace.claims || [];
            console.log(`[TRACE_AUDIT] TRACE HYDRATED from API: ${claims.length} claims`);
        } else {
            console.log(`[TRACE_AUDIT] Trace missing in hydration for session ${sessionId}`);
        }

        debugLog('API', `📥 History received: ${data.messages?.length || 0} messages`);
        return data;
    } catch (error) {
        debugError('API', 'History fetch failed', error);
        return { messages: [], current_mode: 'conversation' };
    }
}

/**
 * Stream Nutri's 13-phase reasoning process (Production API)
 * Uses GET /api/chat/stream with typed SSE events
 * 
 * @param {string} message - User input
 * @param {Object} preferences - { audience_mode, optimization_goal, verbosity, execution_mode }
 * @param {Function} onReasoning - Callback for reasoning updates: (statusMessage) => void
 * @param {Function} onToken - Callback for LLM tokens: (token) => void
 * @param {Function} onComplete - Callback when final output is ready: (finalOutput) => void
 * @param {Function} onError - Callback for errors
 * @param {Function} onStatus - Callback for phase status updates: ({ phase, message, profile }) => void
 * @returns {Function} - Abort function
 */
export function streamNutriChat(
    message,
    preferences = {
        audience_mode: 'scientific',
        optimization_goal: 'comfort',
        verbosity: 'medium',
        execution_mode: null
    },
    onReasoning,
    onToken,
    onComplete,
    onError,
    onStatus = null,
    onNutritionReport = null,
    onTrace = null
) {
    const sessionId = getSessionId();
    const controller = new AbortController();

    // Restore missing state variables
    let aborted = false;
    let completed = false;
    let eventSource = null;

    // Identity & Sequence Tracking
    let lastSeq = -1;
    let activeStreamId = null;

    const processSSE = (e, type, handler) => {
        const parsed = safeParseJSON(e.data);
        if (!parsed) return;

        // Reset tracking on new stream_id detection
        const streamId = parsed.stream_id;
        if (streamId && streamId !== activeStreamId) {
            debugLog('SSE', `📡 [NEW] Stream identity detected: ${streamId}`);
            activeStreamId = streamId;
            lastSeq = -1;
        }

        const seq = parsed.seq || parsed.seq_id || 0;
        if (seq > 0 && seq <= lastSeq) {
            debugLog('SSE', `♻️ [DUP/OLD] Dropping seq ${seq} (last=${lastSeq})`);
            return;
        }

        // Update lastSeq
        if (seq > 0) lastSeq = seq;

        handler(parsed, type);
    };

    (async () => {
        try {
            const baseURL = await getBackendURL();

            const params = new URLSearchParams({
                message: message,
                session_id: sessionId,
                execution_mode: preferences.execution_mode || '',
                audience_mode: preferences.audience_mode || 'scientific',
                optimization_goal: preferences.optimization_goal || 'comfort',
                verbosity: preferences.verbosity || 'medium',
                x_user_id: getUserId() // Fallback passed as query param for EventSource
            });

            const url = `${baseURL}/api/chat/stream?${params.toString()}`;
            debugLog('SSE', `🔗 [OPEN] Opening EventSource: ${url}`);

            eventSource = new EventSource(url);

            const cleanup = () => {
                if (eventSource) {
                    debugLog('SSE', '🔌 [CLOSE] Closing EventSource');
                    eventSource.close();
                    eventSource = null;
                }
            };

            eventSource.onmessage = (e) => {
                processSSE(e, 'status', (data) => {
                    debugLog('SSE', '🧠 [REASONING] received', data);
                    if (onStatus) onStatus(data);
                    if (onReasoning) onReasoning(data.message || e.data);
                });
            };

            eventSource.addEventListener('nutrition_report', (e) => {
                processSSE(e, 'nutrition_report', (data) => {
                    debugLog('SSE', '🥗 [NUTRITION_REPORT] received', data);
                    if (onNutritionReport) onNutritionReport(data);
                });
            });

            eventSource.addEventListener('execution_trace', (e) => {
                processSSE(e, 'execution_trace', (data) => {
                    debugLog('SSE', '🕵️ [EXECUTION_TRACE] received');

                    // [TRACE_AUDIT] Step 6: Frontend acceptance
                    const rawTrace = data.content || data; // Handle envelope
                    const claimCount = rawTrace.claims ? rawTrace.claims.length : 0;
                    console.log(`[TRACE_AUDIT] TRACE RECEIVED: ${claimCount} claims`);

                    if (onTrace) onTrace(data);
                });
            });

            eventSource.addEventListener('token', (e) => {
                processSSE(e, 'token', (data) => {
                    let token = data.content || data.token || e.data;
                    onToken(token);
                });
            });

            eventSource.addEventListener('done', (e) => {
                if (completed) return; // Ignore double-DONE

                processSSE(e, 'done', (data) => {
                    debugLog('SSE', '✅ [DONE] Completion signal received');
                    completed = true;
                    if (onComplete) onComplete(data || { status: 'success' });
                    cleanup();
                });
            });

            // Explicit backend error event
            eventSource.addEventListener('error_event', (e) => {
                processSSE(e, 'error_event', (data) => {
                    const errorMsg = data.message || e.data || 'Backend execution failed';
                    debugError('SSE', `❌ [ERROR_EVENT] ${errorMsg}`);
                    onError(new Error(errorMsg));
                    completed = true;
                    cleanup();
                });
            });

            // Generic EventSource error (usually network/timeout/closure)
            eventSource.onerror = (e) => {
                if (completed || aborted) return;

                debugError('SSE', '⚠️ [CONNECTION_ERROR] Stream failed or closed.');
                cleanup();
                onError(new Error('Stream connection interrupted.'));
            };

            controller.signal.addEventListener('abort', cleanup);


        } catch (error) {
            if (!aborted) {
                console.error('SSE Setup Error:', error);
                onError(error);
            }
        }
    })();

    return () => {
        aborted = true;
        controller.abort();
    };
}


/**
 * Change response mode
 * 
 * @param {string} mode - 'simple' | 'standard' | 'chemistry'
 * @returns {Promise<boolean>} - Success status
 */
export async function setMode(mode) {
    try {
        const baseURL = await getBackendURL();
        const response = await fetch(`${baseURL}/api/mode`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ mode }),
        });

        return response.ok;

    } catch (error) {
        console.error('Failed to set mode:', error);
        return false;
    }
}

/**
 * Get system health and resource status
 */
export async function getHealth() {
    try {
        const baseURL = await getBackendURL();
        const response = await fetch(`${baseURL}/health`, {
            headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        if (!response.ok) return { status: 'offline' };
        return await response.json();
    } catch (e) {
        return { status: 'error', error: e.message };
    }
}

/**
 * Get system stats
 */
export async function getStats() {
    try {
        const baseURL = await getBackendURL();
        const response = await fetch(`${baseURL}/api/stats`);
        if (!response.ok) return { recipes: 0, ingredients: 0, papers: 0 };
        return await response.json();
    } catch (error) {
        console.error('Failed to get stats:', error);
        return { recipes: 0, ingredients: 0, papers: 0 };
    }
}

// ============================================================================ 
// EXPORT ERROR TYPES (for React components to catch)
// ============================================================================ 

export { APIError, NetworkError, TimeoutError };
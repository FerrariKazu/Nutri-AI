/**
 * Pure JavaScript API Client
 * NO REACT - Just plain imperative functions
 * Handles all networking, streaming, errors, retries
 */

import { getAuthToken, ensureAuth, getUserId } from '../utils/memoryManager';

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
const DEBUG_MODE = false;

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
    const isDev = import.meta.env.DEV;

    console.error(`${prefix} ${message}`);
    if (error) {
        const errorDetails = {
            name: error.name,
            message: error.message,
            status: error.status,
            body: error.body,
            stack: error.stack
        };

        if (isDev) {
            console.error(`${prefix} DETAILED ERROR:`, errorDetails);
        } else {
            console.error(`${prefix} ${error.name}: ${error.message} (Status: ${error.status || 'N/A'})`);
        }
    }
}

/**
 * Runtime Backend Detection & Resolution
 * Priority: 1. window.__NUTRI_BACKEND_URL__ (Deployment injection)
 *           2. import.meta.env.VITE_BACKEND_URL (Build-time config)
 *           3. location.origin (Same-origin fallback)
 */
async function resolveBackend() {
    debugLog('CONNECTIVITY', '🔍 Resolving final backend identity...');

    let resolved = '';

    // 1. Runtime Override (Priority 1)
    if (window.__NUTRI_BACKEND_URL__) {
        resolved = window.__NUTRI_BACKEND_URL__.replace(/\/$/, '');
        debugLog('CONNECTIVITY', `🏢 [PRIORITY 1] Injected Backend: ${resolved}`);
    }
    // 2. Build-time Config (Priority 2)
    else if (import.meta.env.VITE_BACKEND_URL) {
        resolved = import.meta.env.VITE_BACKEND_URL.replace(/\/$/, '');
        debugLog('CONNECTIVITY', `🏗️ [PRIORITY 2] Env Backend: ${resolved}`);
    }
    // 3. Same-origin fallback
    else {
        // In local development, location.origin is usually 5173, so we NEED the Vite Proxy logic
        // but it must NOT be forced in production.
        const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

        if (isLocalHost && !import.meta.env.PROD) {
            resolved = ''; // Use Vite Proxy
            debugLog('CONNECTIVITY', `🛡️ [FALLBACK] Localhost detected. Using relative URL (Vite Proxy).`);
        } else {
            resolved = window.location.origin;
            debugLog('CONNECTIVITY', `🌐 [FALLBACK] Same-Origin Resolution: ${resolved}`);
        }
    }

    console.log(`%c [CONNECTIVITY] Resolved: "${resolved || '(Relative/Proxy)'}" `, "background: #1e293b; color: #38bdf8; font-weight: bold; padding: 2px 4px;");
    return resolved;
}

// Cached backend URL promise
let backendUrlPromise = null;

function getBackendURL() {
    if (!backendUrlPromise) {
        backendUrlPromise = resolveBackend();
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
    constructor(message, status, response, body = null) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.response = response;
        this.body = body;
        // The stack is automatically captured by the Error constructor
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


/**
 * Helper to handle response and throw APIError with body
 */
async function handleAPIResponse(response, customMessage = null) {
    if (response.ok) return response;

    let body = null;
    try {
        const text = await response.text();
        try {
            body = JSON.parse(text);
        } catch (e) {
            body = text;
        }
    } catch (e) {
        body = "(Could not read response body)";
    }

    const message = customMessage || `API Error: ${response.status} ${response.statusText}`;
    throw new APIError(message, response.status, response, body);
}

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

    // ========== [REQUEST] Telemetry ==========
    console.log(`%c [REQUEST] url=${baseURL}/api/chat origin=${window.location.origin} resolved_backend=${baseURL || '(Relative)'} `, "color: #94a3b8; font-family: monospace; font-size: 10px;");

    try {
        const response = await retry(async () => {
            const token = await ensureAuth(baseURL);
            const res = await fetch(`${baseURL}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'ngrok-skip-browser-warning': 'true'
                },
                body: JSON.stringify({ prompt, mode }),
                signal
            });

            return await handleAPIResponse(res, "Direct chat failed");
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
            const token = await ensureAuth(baseURL);
            const response = await fetch(`${baseURL}/api/chat/stream?${params.toString()}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'ngrok-skip-browser-warning': 'true'
                },
                signal
            });

            await handleAPIResponse(response, "Stream initiation failed");
            const reader = response.body.getReader();

            debugLog('STREAM', '🟢 Response OK, starting reader...');

            // Get reader from response body
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
        const token = await ensureAuth(baseURL);
        const response = await fetch(`${baseURL}/api/conversations`, {
            headers: {
                'ngrok-skip-browser-warning': 'true',
                'Authorization': `Bearer ${token}`,
            }
        });

        await handleAPIResponse(response, "Failed to fetch list");

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
        const token = await ensureAuth(baseURL);
        const response = await fetch(`${baseURL}/api/conversation`, {
            method: 'POST',
            headers: {
                'ngrok-skip-browser-warning': 'true',
                'Authorization': `Bearer ${token}`,
            }
        });

        await handleAPIResponse(response, "Conversation creation failed");

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
        const token = await ensureAuth(baseURL);
        const response = await fetch(`${baseURL}/api/conversation?session_id=${sessionId}`, {
            headers: {
                'ngrok-skip-browser-warning': 'true',
                'Authorization': `Bearer ${token}`,
            }
        });

        await handleAPIResponse(response, "History fetch failed");

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
    onTrace = null,
    onMemoryInsight = null,
    onAdversarialCritique = null,
    image = null
) {
    const sessionId = getSessionId();
    const controller = new AbortController();
    let aborted = false;
    let completed = false;
    let eventSource = null;
    let lastSeq = -1;
    let activeStreamId = null;

    /**
     * Unified handler for parsed SSE events
     */
    function handleIncomingParsedEvent(parsed) {
        if (aborted || completed) return;
        const type = parsed.type || 'status';
        
        // Identity & Sequence Tracking
        const streamId = parsed.stream_id;
        if (streamId && streamId !== activeStreamId) {
            activeStreamId = streamId;
            lastSeq = -1;
        }

        const seq = parsed.seq || parsed.seq_id || 0;
        if (seq > 0 && seq <= lastSeq) return;
        if (seq > 0) lastSeq = seq;
        
        // Dispatch to handlers
        if (type === 'status' || !type) {
            if (onStatus) onStatus(parsed);
            if (onReasoning) onReasoning(parsed.message || '');
        } else if (type === 'nutrition_report') {
            if (onNutritionReport) onNutritionReport(parsed);
        } else if (type === 'execution_trace') {
            if (onTrace) onTrace(parsed);
        } else if (type === 'memory_insight') {
            if (onMemoryInsight) onMemoryInsight(parsed);
        } else if (type === 'adversarial_critique') {
            if (onAdversarialCritique) onAdversarialCritique(parsed);
        } else if (type === 'token') {
            const token = parsed.text || parsed.token || '';
            if (onToken) onToken(token);
        }
    }

    let retryCount = 0;
    const MAX_SSE_RETRIES = 5;

    const connect = async () => {
        if (aborted || completed) return;

        try {
            const baseURL = await getBackendURL();
            const accessToken = await ensureAuth(baseURL);

            // 📸 [VISION SIDECAR] If image present, MUST use POST for streaming
            if (image && image.b64) {
                const response = await fetch(`${baseURL}/api/chat`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${accessToken}`
                    },
                    body: JSON.stringify({
                        session_id: sessionId,
                        message: message,
                        preferences: preferences,
                        execution_mode: preferences.execution_mode,
                        image_b64: image.b64,
                        image_media_type: image.media_type
                    }),
                    signal: controller.signal
                });

                if (!response.ok) {
                    const err = await response.json().catch(() => ({ detail: 'Network error' }));
                    throw new Error(err.detail || 'Failed to start chat session');
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop(); // Keep partial line in buffer

                    for (const line of lines) {
                        const trimmedLine = line.trim();
                        if (!trimmedLine.startsWith('data: ')) continue;
                        const dataStr = trimmedLine.replace(/^data: /, '').trim();
                        if (!dataStr) continue;

                        if (dataStr === '[DONE]') {
                            completed = true;
                            if (onComplete) onComplete();
                            return;
                        }

                        const parsed = safeParseJSON(dataStr);
                        if (parsed) handleIncomingParsedEvent(parsed);
                    }
                }
                return;
            }

            // Standard GET-based EventSource for text-only queries
            const params = new URLSearchParams({
                message: message,
                session_id: sessionId,
                execution_mode: preferences.execution_mode || '',
                audience_mode: preferences.audience_mode || 'scientific',
                optimization_goal: preferences.optimization_goal || 'comfort',
                verbosity: preferences.verbosity || 'medium',
                access_token: accessToken,
                run_id: preferences.run_id || ''
            });

            const url = `${baseURL}/api/chat/stream?${params.toString()}`;
            eventSource = new EventSource(url);

            const cleanup = () => {
                if (eventSource) {
                    eventSource.close();
                    eventSource = null;
                }
            };

            eventSource.onmessage = (e) => {
                const parsed = safeParseJSON(e.data);
                if (parsed) handleIncomingParsedEvent(parsed);
            };

            const eventTypes = ['nutrition_report', 'execution_trace', 'memory_insight', 'adversarial_critique', 'token', 'done', 'error_event'];
            eventTypes.forEach(evt => {
                eventSource.addEventListener(evt, (e) => {
                    if (evt === 'done') {
                        completed = true;
                        if (onComplete) onComplete();
                        cleanup();
                        return;
                    }
                    if (evt === 'error_event') {
                        const data = safeParseJSON(e.data);
                        onError(new Error(data?.message || 'Backend error'));
                        cleanup();
                        return;
                    }
                    const parsed = safeParseJSON(e.data);
                    if (parsed) handleIncomingParsedEvent({ ...parsed, type: evt });
                });
            });

            eventSource.onerror = (e) => {
                if (completed || aborted) return;
                cleanup();

                if (retryCount < MAX_SSE_RETRIES) {
                    retryCount++;
                    const delay = Math.min(1000 * Math.pow(2, retryCount), 10000);
                    setTimeout(connect, delay);
                } else {
                    onError(new Error('Persistent stream connection failure.'));
                }
            };

            controller.signal.addEventListener('abort', cleanup);

        } catch (error) {
            if (!aborted) {
                onError(error);
            }
        }
    };

    connect();

    return () => {
        aborted = true;
        controller.abort();
    };
}


/**
 * Get the current user's preferences
 */
export async function getPreferences() {
    debugLog('API', '🔄 Fetching user preferences...');
    try {
        const baseURL = await getBackendURL();
        const token = await ensureAuth(baseURL);
        const response = await fetch(`${baseURL}/api/preferences`, {
            headers: {
                'ngrok-skip-browser-warning': 'true',
                'Authorization': `Bearer ${token}`,
            }
        });

        await handleAPIResponse(response, "Failed to fetch preferences");

        const data = await response.json();
        debugLog('API', `📥 Received preferences`, data);
        return data;
    } catch (error) {
        debugError('API', 'Preferences fetch failed', error);
        return null;
    }
}

/**
 * Update the current user's preferences
 */
export async function updatePreferences(preferences) {
    debugLog('API', '📤 Updating user preferences...', preferences);
    try {
        const baseURL = await getBackendURL();
        const token = await ensureAuth(baseURL);
        const response = await fetch(`${baseURL}/api/preferences`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'ngrok-skip-browser-warning': 'true',
                'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify(preferences)
        });

        await handleAPIResponse(response, "Failed to update preferences");

        const data = await response.json();
        debugLog('API', `📥 Update status`, data);
        return data;
    } catch (error) {
        debugError('API', 'Preferences update failed', error);
        throw error;
    }
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
        const token = await ensureAuth(baseURL);
        const response = await fetch(`${baseURL}/api/mode`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                'ngrok-skip-browser-warning': 'true'
            },
            body: JSON.stringify({ mode }),
        });

        await handleAPIResponse(response, "Set mode failed");
        return true;

    } catch (error) {
        debugError('API', 'Failed to set mode', error);
        return false;
    }
}

/**
 * Get system health and resource status
 */
export async function getHealth() {
    try {
        const baseURL = await getBackendURL();
        const token = await ensureAuth(baseURL);
        const response = await fetch(`${baseURL}/api/health`, {
            headers: {
                'ngrok-skip-browser-warning': 'true',
                'Authorization': `Bearer ${token}`
            }
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
        const token = await ensureAuth(baseURL);
        const response = await fetch(`${baseURL}/api/stats`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'ngrok-skip-browser-warning': 'true'
            }
        });
        if (!response.ok) return { recipes: 0, ingredients: 0, papers: 0 };
        return await response.json();
    } catch (error) {
        debugError('API', 'Failed to get stats', error);
        return { recipes: 0, ingredients: 0, papers: 0 };
    }
}

// ============================================================================ 
// EXPORT ERROR TYPES (for React components to catch)
// ============================================================================ 

export { APIError, NetworkError, TimeoutError };
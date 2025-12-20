/**
 * Pure JavaScript API Client
 * NO REACT - Just plain imperative functions
 * Handles all networking, streaming, errors, retries
 */

// ============================================================================ 
// CONFIGURATION
// ============================================================================ 

const LOCAL_BACKEND_URLS = [
    'https://chaim-smokeproof-nonexcitably.ngrok-free.dev',
    'http://localhost:8001',
    'http://localhost:8000',
];

// Fallback if local backend isn't running
const RAILWAY_BACKEND_URL = 'https://nutri-ai.up.railway.app';

let finalBackendURL = '';

async function detectBackend() {
    // 0. Check Environment Variable (Vercel/Vite)
    if (import.meta.env.VITE_API_URL) {
        const envUrl = import.meta.env.VITE_API_URL.replace(/\/$/, ''); // Remove trailing slash
        console.log(`🌍 Using VITE_API_URL: ${envUrl}`);
        return envUrl;
    }

    // 1. Try local URLs first
    for (const url of LOCAL_BACKEND_URLS) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2000); // 2s timeout
            const response = await fetch(`${url}/api/health`, { signal: controller.signal });
            clearTimeout(timeoutId);
            if (response.ok) {
                console.log(`✅ Local Backend detected, using: ${url}`);
                return url;
            }
        } catch (error) {
            // This is expected if the server isn't running on this URL
        }
    }

    // 2. Fallback to Railway
    console.log(`- Local backend not found. Falling back to Railway: ${RAILWAY_BACKEND_URL}`);
    return RAILWAY_BACKEND_URL;
}

// Cached backend URL promise
let backendUrlPromise = null;

function getBackendURL() {
    if (!backendUrlPromise) {
        backendUrlPromise = detectBackend();
    }
    return backendUrlPromise;
}


const API_CONFIG = {
    timeout: 30000,  // 30 seconds
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
function parseJSON(text) {
    try {
        return JSON.parse(text);
    } catch (e) {
        return null;
    }
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

    try {
        const response = await retry(async () => {
            const res = await fetch(`${baseURL}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
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
                const errorData = parseJSON(errorText);

                throw new APIError(
                    errorData?.error || `HTTP ${res.status}: ${res.statusText}`,
                    res.status,
                    errorData
                );
            }

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
                        content = content.replace(/^["\?:\.\s]+/, '');
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

        return sanitizeResponse(await response.json());

    } catch (error) {
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
            const response = await fetch(`${baseURL}/api/chat/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: prompt,
                    mode: mode,
                }),
                signal: combinedSignal,
            });

            if (!response.ok) {
                throw new APIError(
                    `HTTP ${response.status}: ${response.statusText}`,
                    response.status
                );
            }

            // Get reader from response body
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            let fullResponse = '';
            let buffer = '';
            let rawBuffer = ''; // To track raw stream for cleaning
            let previousCleanLength = 0;

            // Read stream
            while (true) {
                const { done, value } = await reader.read();

                if (done) break;
                if (aborted) break;

                // Decode chunk
                buffer += decoder.decode(value, { stream: true });

                // Process complete lines (SSE format)
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // Keep incomplete line in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6); // Remove "data: " prefix

                        if (data === '[DONE]') {
                            break;
                        }

                        try {
                            const parsed = JSON.parse(data);
                            const token = parsed.token || parsed.content || '';
                            const type = parsed.type || 'content';

                            if (token && type === 'content') {
                                // Add to RAW buffer
                                rawBuffer += token;

                                // Clean the entire raw buffer
                                const cleanBuffer = cleanResponse(rawBuffer);

                                // If cleaning resulted in new content, emit it
                                if (cleanBuffer.length > previousCleanLength) {
                                    const newContent = cleanBuffer.slice(previousCleanLength);
                                    fullResponse += newContent;
                                    onToken(newContent, 'content');
                                    previousCleanLength = cleanBuffer.length;
                                }
                            }

                        } catch (e) {
                            // Ignore invalid JSON
                        }
                    }
                }
            }

            // Call completion callback
            if (!aborted && onComplete) {
                onComplete(fullResponse);
            }

        } catch (error) {
            // ... (rest of error handling)
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
 * Get system stats
 * 
 * @returns {Promise<Object>} - { recipes, ingredients, papers, etc. }
 */
export async function getStats() {
    try {
        const baseURL = await getBackendURL();
        const response = await fetch(`${baseURL}/api/stats`);

        if (!response.ok) {
            throw new APIError('Failed to fetch stats', response.status);
        }

        return await response.json();

    } catch (error) {
        console.error('Failed to get stats:', error);
        return {
            recipes: 0,
            ingredients: 0,
            papers: 0,
        };
    }
}

/**
 * Health check
 * 
 * @returns {Promise<boolean>} - Is backend healthy?
 */
export async function healthCheck() {
    try {
        const baseURL = await getBackendURL();
        const response = await fetch(`${baseURL}/api/health`, {
            method: 'GET',
            signal: AbortSignal.timeout(5000), // 5 second timeout
        });

        return response.ok;

    } catch (error) {
        return false;
    }
}

// ============================================================================ 
// EXPORT ERROR TYPES (for React components to catch)
// ============================================================================ 

export { APIError, NetworkError, TimeoutError };
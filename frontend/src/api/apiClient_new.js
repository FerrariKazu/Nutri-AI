/**
 * Production Nutri Chat Stream - Unified API
 * Handles POST /api/chat with typed SSE events
 */

import { getSessionId, getBackendURL } from './apiClient';

export function streamNutriChat(
    message,
    preferences = {
        audience_mode: 'scientific',
        optimization_goal: 'comfort',
        verbosity: 'medium'
    },
    onReasoning,
    onToken,
    onComplete,
    onError
) {
    const sessionId = getSessionId();
    const controller = new AbortController();
    let aborted = false;

    (async () => {
        try {
            const baseURL = await getBackendURL();
            const response = await fetch(`${baseURL}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'ngrok-skip-browser-warning': 'true',
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    message: message,
                    preferences: preferences
                }),
                signal: controller.signal
            });

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let currentEvent = 'token';

            while (true) {
                const { done, value } = await reader.read();
                if (done || aborted) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    const trimmed = line.trim();
                    if (!trimmed) continue;

                    if (trimmed.startsWith('event: ')) {
                        currentEvent = trimmed.slice(7).trim();
                    } else if (trimmed.startsWith('data: ')) {
                        const data = trimmed.slice(6).trim();
                        if (!data) continue;

                        try {
                            if (currentEvent === 'token') {
                                onToken(data);
                            } else if (currentEvent === 'reasoning') {
                                onReasoning(data);
                            } else if (currentEvent === 'final') {
                                const parsed = JSON.parse(data);
                                onComplete(parsed.content || parsed);
                            } else if (currentEvent === 'error') {
                                throw new Error(data);
                            }
                        } catch (e) {
                            console.error('SSE Parse Error:', e, data);
                        }
                    }
                }
            }
        } catch (error) {
            if (!aborted) {
                console.error('Stream Error:', error);
                onError(error);
            }
        }
    })();

    return () => {
        aborted = true;
        controller.abort();
    };
}

/**
 * Configuration for API and WebSocket URLs
 * Automatically detects environment (dev/prod)
 */

export const getWebSocketURL = () => {
    // In development, point to local backend
    if (import.meta.env.DEV) {
        return 'ws://localhost:8000/ws';
    }

    // In production, assume served from same origin (FastAPI serving React build)
    // Or point to the configured backend URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // If you deploy frontend separately (e.g. Vercel), replace this with your backend domain
    // const backendHost = 'nutri-ai-production.up.railway.app';
    const host = window.location.host;

    return `${protocol}//${host}/ws`;
};

export const getApiURL = () => {
    if (import.meta.env.DEV) {
        return 'http://localhost:8000';
    }
    return ''; // Relative path in production
};

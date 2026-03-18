/**
 * chatStorage.js
 * Handles saving and loading of chat messages to localStorage to provide
 * persistence across browser reloads.
 */

const STORAGE_KEY = 'nutri_chat';

export function saveMessages(messages) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    } catch (e) {
        console.warn('[CHAT_STORAGE] Failed to save messages:', e);
    }
}

export function loadMessages() {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return JSON.parse(stored || "[]");
    } catch (e) {
        console.warn('[CHAT_STORAGE] Failed to load messages:', e);
        return [];
    }
}

export function clearMessages() {
    try {
        localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
        console.warn('[CHAT_STORAGE] Failed to clear messages:', e);
    }
}

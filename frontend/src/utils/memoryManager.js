/**
 * Memory Manager for User Identity & Preferences
 * 
 * Auth Flow:
 *   1. Frontend calls POST /api/dev-login → backend signs JWT
 *   2. Token cached in localStorage
 *   3. All API calls send Authorization: Bearer <token>
 *   4. No secret ever touches the client
 */

const AUTH_TOKEN_KEY = "nutri_auth_token";
const AUTH_USER_KEY = "nutri_user_id";
const PREFS_KEY = "nutri_user_prefs";
const MAX_STORAGE_SIZE = 5 * 1024 * 1024;

// ─── Auth Token Management ──────────────────────────────────────

/**
 * Decode JWT payload (no verification — that's the server's job)
 */
function decodeTokenPayload(token) {
    try {
        const parts = token.split(".");
        if (parts.length !== 3) return null;
        const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
        return payload;
    } catch {
        return null;
    }
}

/**
 * Check if the cached token is expired
 */
export const isTokenExpired = () => {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!token) return true;

    const payload = decodeTokenPayload(token);
    if (!payload?.exp) return true;

    // Expire 60s early to avoid race conditions
    return Date.now() / 1000 > payload.exp - 60;
};

/**
 * Get the cached auth token. Returns null if missing or expired.
 */
export const getAuthToken = () => {
    if (isTokenExpired()) return null;
    return localStorage.getItem(AUTH_TOKEN_KEY);
};

/**
 * Get user_id from the cached token's sub claim.
 */
export const getUserId = () => {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!token) return localStorage.getItem(AUTH_USER_KEY) || null;

    const payload = decodeTokenPayload(token);
    return payload?.sub || localStorage.getItem(AUTH_USER_KEY) || null;
};

/**
 * Dev Login: Calls POST /api/dev-login to obtain a backend-signed JWT.
 * @param {string} baseURL - Resolved backend URL
 * @param {string|null} existingUserId - Reuse existing user_id if available
 * @returns {Promise<string>} The auth token
 */
export const loginDev = async (baseURL = "", existingUserId = null) => {
    const userId = existingUserId || localStorage.getItem(AUTH_USER_KEY) || null;

    const response = await fetch(`${baseURL}/api/dev-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(userId ? { user_id: userId } : {}),
    });

    if (!response.ok) {
        throw new Error(`Dev login failed: ${response.status}`);
    }

    const data = await response.json();

    // Cache token + user_id
    localStorage.setItem(AUTH_TOKEN_KEY, data.token);
    localStorage.setItem(AUTH_USER_KEY, data.user_id);

    console.log("[AUTH] Dev token acquired for user:", data.user_id);
    return data.token;
};

/**
 * Ensure we have a valid token. Auto-login if expired or missing.
 * @param {string} baseURL - Backend URL
 * @returns {Promise<string>} Valid auth token
 */
export const ensureAuth = async (baseURL = "") => {
    const existing = getAuthToken();
    if (existing) return existing;

    return await loginDev(baseURL);
};

/**
 * Clear auth state (logout)
 */
export const clearAuth = () => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    console.log("[AUTH] Cleared auth state");
};

// ─── Preferences (unchanged) ────────────────────────────────────

export const savePreferences = (prefs) => {
    const userId = getUserId();
    const stored = localStorage.getItem(PREFS_KEY);
    const existing = stored ? JSON.parse(stored) : {};

    const updated = {
        ...existing,
        ...prefs,
        userId,
        updated_at: new Date().toISOString()
    };

    const sizeEstimate = JSON.stringify(updated).length;
    if (sizeEstimate > MAX_STORAGE_SIZE) {
        console.warn("[MEMORY] Preferences exceed 5MB limit.");
        return userId;
    }

    localStorage.setItem(PREFS_KEY, JSON.stringify(updated));
    return userId;
};

export const loadPreferences = () => {
    const stored = localStorage.getItem(PREFS_KEY);
    if (!stored) return null;
    try {
        return JSON.parse(stored);
    } catch {
        return null;
    }
};

export const clearPreferences = () => {
    localStorage.removeItem(PREFS_KEY);
};

export const getStorageUsage = () => {
    const prefs = localStorage.getItem(PREFS_KEY);
    return prefs ? prefs.length : 0;
};

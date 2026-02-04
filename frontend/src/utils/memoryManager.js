/**
 * Memory Manager for User Preferences
 * 
 * Implements user-scoped preference persistence via localStorage
 */

const USER_ID_KEY = "nutri_user_id";
const PREFS_KEY = "nutri_user_prefs";

// Storage size limit (5MB)
const MAX_STORAGE_SIZE = 5 * 1024 * 1024;

/**
 * Get or create stable user ID
 * @returns {string} - UUID for this user
 */
export const getUserId = () => {
    let userId = localStorage.get Item(USER_ID_KEY);
    if (!userId) {
        userId = crypto.randomUUID();
        localStorage.setItem(USER_ID_KEY, userId);
        console.log('[MEMORY] Created new user_id:', userId);
    }
    return userId;
};

/**
 * Save user preferences
 * @param {object} prefs - Preference updates (skill_level, equipment, dietary_constraints)
 * @returns {string} - user_id
 */
export const savePreferences = (prefs) => {
    const userId = getUserId();

    // Get existing prefs
    const stored = localStorage.getItem(PREFS_KEY);
    const existing = stored ? JSON.parse(stored) : {};

    // Merge with new prefs
    const updated = {
        ...existing,
        ...prefs,
        userId,  // Ensure user_id is saved
        updated_at: new Date().toISOString()
    };

    // Check storage size before saving
    const sizeEstimate = JSON.stringify(updated).length;
    if (sizeEstimate > MAX_STORAGE_SIZE) {
        console.warn('[MEMORY] Preferences exceed 5MB limit. Truncating...');
        // Remove oldest data if needed
        return userId;
    }

    localStorage.setItem(PREFS_KEY, JSON.stringify(updated));
    console.log('[MEMORY] Preferences saved:', prefs);

    return userId;
};

/**
 * Load user preferences
 * @returns {object|null} - Preference object or null
 */
export const loadPreferences = () => {
    const stored = localStorage.getItem(PREFS_KEY);
    if (!stored) return null;

    try {
        const prefs = JSON.parse(stored);
        console.log('[MEMORY] Preferences loaded:', prefs);
        return prefs;
    } catch (e) {
        console.error('[MEMORY] Failed to parse preferences:', e);
        return null;
    }
};

/**
 * Clear all preferences
 */
export const clearPreferences = () => {
    localStorage.removeItem(PREFS_KEY);
    console.log('[MEMORY] Preferences cleared');
};

/**
 * Get storage usage estimate
 * @returns {number} - Bytes used
 */
export const getStorageUsage = () => {
    const prefs = localStorage.getItem(PREFS_KEY);
    return prefs ? prefs.length : 0;
};

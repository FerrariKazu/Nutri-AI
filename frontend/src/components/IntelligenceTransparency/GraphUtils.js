/**
 * GraphUtils.js
 * 
 * Pure mathematical utilities for scientific graph rendering. (v1.2.9)
 * NO side effects. NO DOM reads.
 */

/**
 * Single source of truth for node visual size.
 */
export const NODE_RADIUS = 18;

/**
 * Calculates edge endpoints offset by node radius using pure math.
 * 
 * @param {number} x1 Source X
 * @param {number} y1 Source Y
 * @param {number} x2 Target X
 * @param {number} y2 Target Y
 * @returns {Object} {x1_off, y1_off, x2_off, y2_off}
 */
export const calculateEdgeOffsets = (x1, y1, x2, y2) => {
    const angle = Math.atan2(y2 - y1, x2 - x1);

    return {
        x1_off: x1 + Math.cos(angle) * NODE_RADIUS,
        y1_off: y1 + Math.sin(angle) * NODE_RADIUS,
        x2_off: x2 - Math.cos(angle) * NODE_RADIUS,
        y2_off: y2 - Math.sin(angle) * NODE_RADIUS
    };
};

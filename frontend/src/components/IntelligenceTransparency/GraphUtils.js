/**
 * GraphUtils.js
 * 
 * Shared utilities for scientific graph rendering.
 */

export const NODE_RADIUS = 18;

/**
 * Calculates edge endpoints offset by node radius.
 * Prevents arrows from being hidden inside the node circle.
 */
export const calculateEdgeOffsets = (x1, y1, x2, y2) => {
    const angle = Math.atan2(y2 - y1, x2 - x1);

    return {
        x1_offset: x1 + Math.cos(angle) * NODE_RADIUS,
        y1_offset: y1 + Math.sin(angle) * NODE_RADIUS,
        x2_offset: x2 - Math.cos(angle) * NODE_RADIUS,
        y2_offset: y2 - Math.sin(angle) * NODE_RADIUS
    };
};

/**
 * Common glass styling for Intelligence Panel elements.
 */
export const INTELLIGENCE_GLASS_STYLE = "backdrop-blur-[12px] bg-[#1e1e2d] bg-opacity-65 border border-[#7878a0] border-opacity-15 shadow-[0_4px_20px_rgba(0,0,0,0.4)] rounded-[12px]";

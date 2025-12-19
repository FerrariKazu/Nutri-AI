/**
 * Ensure animations don't lag on slower devices
 */

export const useReducedMotion = () => {
    if (typeof window === 'undefined') return false;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    return prefersReducedMotion;
};

export const animationConfig = {
    // Disable heavy animations if user prefers reduced motion
    shouldAnimate: !useReducedMotion(),

    // Adjust particle count based on device
    getOptimalParticleCount: () => {
        if (typeof window === 'undefined') return 15;
        const isMobile = window.innerWidth < 768;
        // navigator.hardwareConcurrency is not supported in all browsers but good proxy where available
        const isSlowDevice = navigator.hardwareConcurrency && navigator.hardwareConcurrency < 4;

        if (isMobile || isSlowDevice) return 15; // Fewer lines
        return 30; // Full effect
    }
};

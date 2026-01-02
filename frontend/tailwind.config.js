/** @type {import('tailwindcss').Config} */
export default {
    darkMode: 'class',
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                // Scientific / Cognitive Palette
                neutral: {
                    950: '#0e0f11', // Material Charcoal
                    900: '#121316',
                    800: '#1a1b1e',
                    700: '#242528',
                    400: '#a1a1aa',
                    100: '#f4f4f5',
                },
                accent: {
                    DEFAULT: '#d97706', // Instrumental Amber (desaturated)
                    muted: '#452e15',
                }
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'], // UI / Labels
                serif: ['"Source Serif 4"', 'Georgia', 'serif'], // Analytical output
                mono: ['"JetBrains Mono"', 'monospace'], // Metrics / Hashes
            },
            animation: {
                'pulse-subtle': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'fade-in': 'fadeIn 0.3s ease-out forwards',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0', transform: 'translateY(2px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
            },
        },
    },
    plugins: [
        require('@tailwindcss/typography'),
    ],
}
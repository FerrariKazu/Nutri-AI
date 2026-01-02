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
                    950: '#0e0e11',
                    900: '#111214',
                    800: '#18191c',
                    700: '#222326',
                    400: '#a1a1aa',
                    100: '#f4f4f5',
                },
                accent: {
                    DEFAULT: '#fb923c', // Subtle orange accent
                    muted: '#432a18',
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
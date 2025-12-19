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
                // Kitchen-inspired color palette
                kitchen: {
                    cream: '#FFF8E7',
                    butter: '#FFE5B4',
                    cinnamon: '#D2691E',
                    coffee: '#6F4E37',
                    mint: '#98FF98',
                    tomato: '#FF6347',
                    lemon: '#FFF44F',
                    olive: '#808000',
                    sage: '#9DC183',
                    honey: '#FFC30B',
                    'bg-dark': '#121212',
                    'card-dark': '#1E1E1E',
                    'text-dark': '#EAE0D5',
                    'border-dark': '#3F3025',
                },
                warm: {
                    50: '#FFF8F0',
                    100: '#FFEDD5',
                    200: '#FED7AA',
                    300: '#FDBA74',
                    400: '#FB923C',
                    500: '#F97316',
                    600: '#EA580C',
                    700: '#C2410C',
                    800: '#9A3412',
                    900: '#7C2D12',
                }
            },
            fontFamily: {
                display: ['Caveat', 'cursive'],
                body: ['Inter', 'system-ui', 'sans-serif'],
            },
            animation: {
                'float': 'float 3s ease-in-out infinite',
                'wiggle': 'wiggle 1s ease-in-out infinite',
                'bounce-slow': 'bounce 3s infinite',
                'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'spin-slow': 'spin 3s linear infinite',
                'star-movement-bottom': 'star-movement-bottom linear infinite alternate',
                'star-movement-top': 'star-movement-top linear infinite alternate',
            },
            keyframes: {
                float: {
                    '0%, 100%': { transform: 'translateY(0px)' },
                    '50%': { transform: 'translateY(-20px)' },
                },
                wiggle: {
                    '0%, 100%': { transform: 'rotate(-3deg)' },
                    '50%': { transform: 'rotate(3deg)' },
                },
                'star-movement-bottom': {
                    '0%': { transform: 'translate(0%, 0%)', opacity: '1' },
                    '100%': { transform: 'translate(-100%, 0%)', opacity: '0' },
                },
                'star-movement-top': {
                    '0%': { transform: 'translate(0%, 0%)', opacity: '1' },
                    '100%': { transform: 'translate(100%, 0%)', opacity: '0' },
                },
            },
            backgroundImage: {
                'kitchen-gradient': 'linear-gradient(135deg, #FFF8E7 0%, #FFE5B4 50%, #FED7AA 100%)',
                'cooking-pattern': "url('/patterns/kitchen-pattern.svg')",
            }
        },
    },
    plugins: [],
}
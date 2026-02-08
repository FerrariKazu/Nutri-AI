import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from "path"
import { execSync } from 'child_process'

// Resolve Git SHA for build identity
let gitSha = process.env.VERCEL_GIT_COMMIT_SHA || 'dev-' + Date.now();
if (!process.env.VERCEL_GIT_COMMIT_SHA) {
    try {
        gitSha = execSync('git rev-parse --short HEAD').toString().trim();
    } catch (e) {
        // Fallback already set
    }
}
// Clean for UI
gitSha = typeof gitSha === 'string' ? gitSha.substring(0, 7) : gitSha;

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    define: {
        'import.meta.env.VITE_GIT_SHA': JSON.stringify(gitSha),
    },
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                secure: false,
            },
            '/ws': {
                target: 'ws://localhost:8000',
                ws: true
            }
        }
    }
})

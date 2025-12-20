import { useState, useEffect } from 'react';
import { ChefHat, Menu, X, Moon, Sun } from 'lucide-react';
import ChatInterface from './components/ChatInterface';
import ModeSelector from './components/ModeSelector';
import StatsPanel from './components/StatsPanel';
import { motion, AnimatePresence } from 'framer-motion';
import ErrorBoundary from './components/ErrorBoundary';

import Silk from './components/Silk';

function App() {
    const [selectedMode, setSelectedMode] = useState('standard');
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [theme, setTheme] = useState(() => {
        if (typeof window !== 'undefined') {
            return localStorage.getItem('theme') || 'light';
        }
        return 'light';
    });

    useEffect(() => {
        const root = window.document.documentElement;
        if (theme === 'dark') {
            root.classList.add('dark');
        } else {
            root.classList.remove('dark');
        }
        localStorage.setItem('theme', theme);
    }, [theme]);

    const toggleTheme = () => {
        setTheme(prev => prev === 'light' ? 'dark' : 'light');
    };

    return (
        <ErrorBoundary>
            <div className="flex h-screen w-screen bg-transparent transition-colors duration-300 relative overflow-hidden touch-pan-y">
                {/* ... existing content ... */}
                <div className="fixed inset-0 z-0">
                    <Silk
                        speed={5}
                        scale={1}
                        color={theme === 'dark' ? '#2d2d2d' : '#F5F5F5'}
                        noiseIntensity={0}
                        rotation={0}
                    />
                </div>

                {/* Mobile backdrop overlay */}
                <AnimatePresence>
                    {isSidebarOpen && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setIsSidebarOpen(false)}
                            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-10 lg:hidden"
                        />
                    )}
                </AnimatePresence>

                {/* Sidebar for Mode Selection */}
                <AnimatePresence>
                    {isSidebarOpen && (
                        <motion.div
                            initial={{ x: -300, opacity: 0 }}
                            animate={{ x: 0, opacity: 1 }}
                            exit={{ x: -300, opacity: 0 }}
                            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                            className="fixed z-20 w-80 max-w-[85vw] h-full bg-stone-100/40 dark:bg-black/40 backdrop-blur-xl border-r-2 border-orange-200/30 dark:border-orange-400/20 flex flex-col lg:hidden"
                        >
                            <div className="p-4 sm:p-6 border-b border-orange-200/30 dark:border-orange-400/20 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <ChefHat className="w-7 h-7 sm:w-8 sm:h-8 text-kitchen-cinnamon" />
                                    <h1 className="text-xl sm:text-2xl font-bold text-kitchen-coffee dark:text-kitchen-text-dark handwritten">
                                        Nutri AI
                                    </h1>
                                </div>
                                <button
                                    onClick={() => setIsSidebarOpen(false)}
                                    className="p-2 text-kitchen-coffee dark:text-kitchen-text-dark hover:bg-white/20 dark:hover:bg-white/10 rounded-full transition-colors"
                                >
                                    <X className="w-6 h-6" />
                                </button>
                            </div>

                            <div className="flex-1 overflow-y-auto p-4 dark:text-kitchen-text-dark">
                                <ModeSelector selectedMode={selectedMode} onSelect={setSelectedMode} />
                                <StatsPanel />
                            </div>

                            <div className="p-4 border-t border-orange-200/30 dark:border-orange-400/20">
                                <button
                                    onClick={toggleTheme}
                                    className="flex items-center justify-center gap-2 w-full p-3 rounded-lg bg-white/30 dark:bg-black/30 hover:bg-white/40 dark:hover:bg-black/40 backdrop-blur-sm transition-colors text-kitchen-coffee dark:text-kitchen-text-dark font-medium"
                                >
                                    {theme === 'light' ? (
                                        <>
                                            <Moon className="w-5 h-5" />
                                            <span className="hidden sm:inline">Switch to Dark Mode</span>
                                            <span className="sm:hidden">Dark</span>
                                        </>
                                    ) : (
                                        <>
                                            <Sun className="w-5 h-5" />
                                            <span className="hidden sm:inline">Switch to Light Mode</span>
                                            <span className="sm:hidden">Light</span>
                                        </>
                                    )}
                                </button>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Desktop Sidebar - always visible */}
                <div className="hidden lg:flex lg:relative z-20 w-80 h-full bg-stone-100/30 dark:bg-black/30 backdrop-blur-xl border-r-2 border-orange-200/30 dark:border-orange-400/20 flex-col">
                    <div className="p-6 border-b border-orange-200/30 dark:border-orange-400/20 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <ChefHat className="w-8 h-8 text-kitchen-cinnamon" />
                            <h1 className="text-2xl font-bold text-kitchen-coffee dark:text-kitchen-text-dark handwritten">
                                Nutri AI
                            </h1>
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 dark:text-kitchen-text-dark">
                        <ModeSelector selectedMode={selectedMode} onSelect={setSelectedMode} />
                        <StatsPanel />
                    </div>

                    <div className="p-4 border-t border-orange-200/30 dark:border-orange-400/20">
                        <button
                            onClick={toggleTheme}
                            className="flex items-center justify-center gap-2 w-full p-3 rounded-lg bg-white/30 dark:bg-black/30 hover:bg-white/40 dark:hover:bg-black/40 backdrop-blur-sm transition-colors text-kitchen-coffee dark:text-kitchen-text-dark font-medium"
                        >
                            {theme === 'light' ? (
                                <>
                                    <Moon className="w-5 h-5" />
                                    <span>Switch to Dark Mode</span>
                                </>
                            ) : (
                                <>
                                    <Sun className="w-5 h-5" />
                                    <span>Switch to Light Mode</span>
                                </>
                            )}
                        </button>
                    </div>
                </div>

                {/* Main Content Area */}
                <div className="flex-1 flex flex-col h-full relative z-5">
                    {/* Mobile Header */}
                    <div className="lg:hidden h-14 sm:h-16 bg-white/20 dark:bg-black/20 backdrop-blur-xl border-b border-orange-200/30 dark:border-orange-400/20 flex items-center px-4 justify-between shrink-0">
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setIsSidebarOpen(true)}
                                className="p-2 -ml-2 text-kitchen-coffee dark:text-kitchen-text-dark hover:bg-white/20 dark:hover:bg-white/10 rounded-lg transition-colors"
                            >
                                <Menu className="w-6 h-6" />
                            </button>
                            <ChefHat className="w-6 h-6 text-kitchen-cinnamon" />
                            <span className="font-bold text-kitchen-coffee dark:text-kitchen-text-dark">Nutri AI</span>
                        </div>
                        <button
                            onClick={toggleTheme}
                            className="p-2 text-kitchen-coffee dark:text-kitchen-text-dark hover:bg-white/20 dark:hover:bg-white/10 rounded-lg transition-colors"
                        >
                            {theme === 'light' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
                        </button>
                    </div>

                    {/* Chat Area */}
                    <div className="flex-1 h-full overflow-hidden bg-transparent">
                        <ChatInterface currentMode={selectedMode} />
                    </div>
                </div>
            </div>
        </ErrorBoundary>
    );
}

export default App;
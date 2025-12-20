import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null
        };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        this.setState({
            error: error,
            errorInfo: errorInfo
        });

        // Log to console for extreme debugging
        console.error('🔥 REACT CRASH DETECTED:', error);
        console.error('🛠️ COMPONENT STACK:', errorInfo.componentStack);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="fixed inset-0 flex items-center justify-center bg-black/80 backdrop-blur-md z-[999] p-4">
                    <div className="bg-white dark:bg-zinc-900 border-4 border-red-600 rounded-3xl p-6 sm:p-10 max-w-2xl w-full shadow-[0_0_50px_rgba(220,38,38,0.5)] animate-in zoom-in-95 duration-300">
                        <div className="flex flex-col items-center text-center space-y-6">
                            <div className="bg-red-100 dark:bg-red-900/30 p-4 rounded-full">
                                <AlertTriangle className="w-12 h-12 text-red-600" />
                            </div>

                            <div className="space-y-2">
                                <h1 className="text-3xl font-bold text-zinc-900 dark:text-white">Application Crashed</h1>
                                <p className="text-zinc-600 dark:text-zinc-400">
                                    A critical error occurred that could not be recovered automatically.
                                </p>
                            </div>

                            <div className="w-full text-left space-y-4">
                                <div className="space-y-1">
                                    <div className="text-[10px] font-bold text-red-600 dark:text-red-400 uppercase tracking-widest">ERROR MESSAGE</div>
                                    <div className="p-3 bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-900/20 rounded-xl font-mono text-sm text-red-800 dark:text-red-200 break-all">
                                        {this.state.error?.toString() || 'Unknown React Error'}
                                    </div>
                                </div>

                                {this.state.errorInfo && (
                                    <div className="space-y-1">
                                        <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">COMPONENT STACK</div>
                                        <div className="p-3 bg-zinc-50 dark:bg-black border border-zinc-200 dark:border-zinc-800 rounded-xl font-mono text-[10px] leading-relaxed text-zinc-500 dark:text-zinc-400 overflow-auto max-h-48 whitespace-pre">
                                            {this.state.errorInfo.componentStack}
                                        </div>
                                    </div>
                                )}
                            </div>

                            <button
                                onClick={() => window.location.reload()}
                                className="flex items-center gap-2 px-8 py-3 bg-red-600 hover:bg-red-700 text-white rounded-2xl font-bold transition-all hover:scale-105 active:scale-95 shadow-lg shadow-red-600/30"
                            >
                                <RefreshCw className="w-5 h-5" />
                                Reload Application
                            </button>

                            <p className="text-[10px] text-zinc-400">
                                The developers have been notified (check console for full logs).
                            </p>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;

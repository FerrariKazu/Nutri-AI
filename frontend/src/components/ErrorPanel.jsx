import React from 'react';
import { X, AlertCircle } from 'lucide-react';

const ErrorPanel = ({ error, onDismiss }) => {
    if (!error) return null;

    return (
        <div className="fixed bottom-4 right-4 left-4 sm:left-auto sm:max-w-md bg-white dark:bg-zinc-900 border-2 border-red-500 shadow-2xl rounded-2xl overflow-hidden z-[100] animate-in slide-in-from-bottom-4 duration-300">
            <div className="bg-red-500 p-3 flex items-center justify-between text-white">
                <div className="flex items-center gap-2 font-bold">
                    <AlertCircle className="w-5 h-5" />
                    <span>Extreme Debug: Error Detected</span>
                </div>
                <button
                    onClick={onDismiss}
                    className="p-1 hover:bg-white/20 rounded-full transition-colors"
                >
                    <X className="w-5 h-5" />
                </button>
            </div>

            <div className="p-4 space-y-3">
                <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                    <div className="col-span-1 text-gray-500 dark:text-gray-400">TYPE</div>
                    <div className="col-span-2 font-bold text-red-600 dark:text-red-400 break-all">{error.type || 'Unknown'}</div>

                    <div className="col-span-1 text-gray-500 dark:text-gray-400">STATUS</div>
                    <div className="col-span-2 font-bold">{error.status || 'N/A'}</div>

                    <div className="col-span-1 text-gray-500 dark:text-gray-400">MESSAGE</div>
                    <div className="col-span-2 break-words">{error.message || 'No message provided'}</div>
                </div>

                {error.response && (
                    <div className="space-y-1">
                        <div className="text-[10px] text-gray-500 dark:text-gray-400 font-mono">BACKEND RESPONSE BODY</div>
                        <pre className="p-2 bg-gray-100 dark:bg-black rounded-lg text-[10px] font-mono overflow-auto max-h-40 border border-gray-200 dark:border-zinc-800">
                            {JSON.stringify(error.response, null, 2)}
                        </pre>
                    </div>
                )}

                <div className="pt-2 text-[10px] text-gray-400 dark:text-zinc-500 italic text-center">
                    Check browser console for full stack trace and request logs.
                </div>
            </div>

            <div className="px-4 pb-4">
                <button
                    onClick={onDismiss}
                    className="w-full py-2 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 rounded-xl font-semibold transition-colors text-sm"
                >
                    Dismiss and Retry
                </button>
            </div>
        </div>
    );
};

export default ErrorPanel;

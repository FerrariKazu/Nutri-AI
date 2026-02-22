import React from 'react';
import { Menu } from 'lucide-react';

const timeAgo = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return 'Just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return date.toLocaleDateString();
};

const ChatHeader = ({ title, lastActive, mode, onOpenSidebar }) => {
    return (
        <div className="absolute top-0 left-0 right-0 h-16 bg-neutral-950/80 backdrop-blur-md border-b border-neutral-900 z-20 flex items-center justify-between px-4 md:px-6 animate-fade-in">
            <div className="flex items-center gap-3 overflow-hidden">
                {/* Mobile Hamburger Trigger */}
                <button
                    onClick={onOpenSidebar}
                    className="md:hidden p-2 -ml-2 text-neutral-400 hover:text-neutral-200 active:scale-95 transition-transform"
                    aria-label="Open sidebar"
                >
                    <Menu className="w-5 h-5" />
                </button>

                {/* Compact Brand Logo */}
                <img
                    src="/nutri-logo.png"
                    alt="Nutri"
                    className="nutri-header-logo"
                />

                <div className="flex flex-col overflow-hidden">
                    <h1 className="text-sm font-medium text-neutral-200 tracking-wide font-serif truncate max-w-[200px] md:max-w-md">
                        {title || 'New Conversation'}
                    </h1>
                    <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-neutral-500">
                        <span className="truncate">
                            {lastActive ? `Active ${timeAgo(lastActive)}` : 'Ready'}
                        </span>
                        {mode && (
                            <>
                                <span className="text-neutral-800">•</span>
                                <span className="text-accent/60 truncate">{mode}</span>
                            </>
                        )}
                    </div>
                </div>
            </div>
            {/* Optional right-side controls can go here */}
        </div>
    );
};

export default ChatHeader;

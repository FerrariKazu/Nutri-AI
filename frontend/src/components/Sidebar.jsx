import React, { useEffect, useState } from 'react';
import { Plus, MessageSquare, Clock, ChevronLeft, Menu } from 'lucide-react';

// Writing simple helper to avoid dependency bloat if not present.

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
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
};

const Sidebar = ({
    isOpen,
    setIsOpen,
    conversations,
    currentSessionId,
    onSelectSession,
    onNewChat
}) => {
    // Lock body scroll when mobile sidebar is open
    useEffect(() => {
        if (isOpen && window.innerWidth < 768) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
        return () => { document.body.style.overflow = ''; };
    }, [isOpen]);

    return (
        <>
            {/* Mobile Backdrop - Fade In */}
            <div
                className={`
                    fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden transition-opacity duration-300
                    ${isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}
                `}
                onClick={() => setIsOpen(false)}
            />

            {/* Sidebar Container - Drawer */}
            <div className={`
                fixed top-0 left-0 h-full bg-neutral-950 border-r border-neutral-900 z-50
                w-[280px] shadow-2xl transform transition-transform duration-300 ease-in-out
                ${isOpen ? 'translate-x-0' : '-translate-x-full'}
                md:translate-x-0 md:static md:shrink-0 md:w-72 md:shadow-none
            `}>
                <div className="flex flex-col h-full">
                    {/* Header */}
                    <div className="p-4 border-b border-neutral-900 flex items-center justify-between h-16">
                        <h2 className="text-sm font-serif text-neutral-400 tracking-wide">YOUR CHATS</h2>
                        <button
                            onClick={onNewChat}
                            className="p-2 hover:bg-neutral-900 rounded-full text-neutral-400 hover:text-accent transition-colors group"
                            title="New Chat"
                        >
                            <Plus className="w-5 h-5 group-hover:rotate-90 transition-transform" />
                        </button>
                    </div>

                    {/* List */}
                    <div className="flex-1 overflow-y-auto py-2">
                        {conversations.length === 0 ? (
                            <div className="p-8 text-center opacity-30">
                                <MessageSquare className="w-8 h-8 mx-auto mb-2" />
                                <p className="text-xs font-mono">NO HISTORY</p>
                            </div>
                        ) : (
                            conversations.map((conv) => (
                                <button
                                    key={conv.session_id}
                                    onClick={() => {
                                        onSelectSession(conv.session_id);
                                        // Auto-close on mobile only
                                        if (window.innerWidth < 768) setIsOpen(false);
                                    }}
                                    className={`
                                        w-full text-left p-4 border-l-2 transition-all hover:bg-neutral-900/50
                                        flex flex-col gap-1 group
                                        ${conv.session_id === currentSessionId
                                            ? 'border-accent bg-neutral-900/30'
                                            : 'border-transparent opacity-60 hover:opacity-100'}
                                    `}
                                >
                                    <div className="flex justify-between items-baseline">
                                        <span className={`
                                            text-sm font-medium truncate max-w-[70%]
                                            ${conv.session_id === currentSessionId ? 'text-neutral-200' : 'text-neutral-400'}
                                        `}>
                                            {conv.title}
                                        </span>
                                        <span className="text-[10px] font-mono text-neutral-600 shrink-0">
                                            {timeAgo(conv.last_active)}
                                        </span>
                                    </div>
                                    <span className="text-xs text-neutral-500 truncate font-sans">
                                        {conv.preview}
                                    </span>
                                </button>
                            ))
                        )}
                    </div>

                    {/* Footer / Branding */}
                    <div className="p-4 border-t border-neutral-900 text-center bg-neutral-950">
                        <p className="text-[10px] text-neutral-700 font-mono tracking-widest uppercase">
                            Nutri-AI v1.3
                        </p>
                    </div>
                </div>
            </div>
            {/* Removed internal floating trigger - now handled by header */}
        </>
    );
};

export default Sidebar;

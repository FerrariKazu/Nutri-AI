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
    // 1. ESC Key Listener (Cleanup-aware)
    useEffect(() => {
        if (!isOpen) return;

        const handleEscape = (e) => {
            if (e.key === 'Escape') setIsOpen(false);
        };

        window.addEventListener('keydown', handleEscape);
        return () => window.removeEventListener('keydown', handleEscape);
    }, [isOpen, setIsOpen]);

    // 2. Body Scroll Lock (Global for all screens when open)
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
        return () => { document.body.style.overflow = ''; };
    }, [isOpen]);

    return (
        <>
            {/* Sidebar Overlay (Dim Background) */}
            <div
                className={`sidebar-overlay ${isOpen ? 'active' : ''}`}
                onClick={() => setIsOpen(false)}
            />

            {/* Sidebar Container (Fixed Overlay) */}
            <div className={`sidebar ${isOpen ? 'open' : ''}`}>
                <div className="flex flex-col h-full w-full">

                    {/* Top Action: New Chat */}
                    <div className="p-4 pt-0">
                        <button
                            onClick={onNewChat}
                            className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-accent/10 hover:bg-accent/20 border border-accent/20 rounded-xl text-accent text-sm font-medium transition-all active:scale-[0.98]"
                        >
                            <Plus className="w-4 h-4" />
                            <span>New Conversation</span>
                        </button>
                    </div>

                    <div className="mx-6 border-b border-white/5 my-2"></div>

                    {/* Section Label */}
                    <div className="px-6 py-2">
                        <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-neutral-600">
                            Recent
                        </span>
                    </div>

                    {/* Chat List */}
                    <div className="flex-1 overflow-y-auto custom-scrollbar pb-6">
                        {conversations.length === 0 ? (
                            <div className="p-12 text-center opacity-20">
                                <MessageSquare className="w-8 h-8 mx-auto mb-2" />
                                <p className="text-[10px] font-mono tracking-widest">NO HISTORY</p>
                            </div>
                        ) : (
                            conversations.map((conv) => (
                                <div
                                    key={conv.session_id}
                                    onClick={() => {
                                        onSelectSession(conv.session_id);
                                        setIsOpen(false); // Close on selection
                                    }}
                                    className={`chat-item ${conv.session_id === currentSessionId ? 'active' : ''}`}
                                >
                                    <div className="flex justify-between items-start gap-2">
                                        <span className="chat-item-title">{conv.title}</span>
                                        <span className="chat-item-meta">{timeAgo(conv.last_active)}</span>
                                    </div>
                                    <span className="chat-item-preview">
                                        {conv.preview || 'No messages yet...'}
                                    </span>
                                </div>
                            ))
                        )}
                    </div>

                    {/* Footer / Branding */}
                    <div className="p-6 border-t border-white/5 bg-neutral-950/50 backdrop-blur-sm">
                        <p className="text-[9px] text-neutral-700 font-mono tracking-[0.3em] uppercase text-center opacity-50">
                            Nutri Operational Layer v1.4
                        </p>
                    </div>
                </div>
            </div>
        </>
    );
};

export default Sidebar;

import React, { useState, useRef, useEffect } from 'react';
import { Terminal, Send, ShieldCheck, Cpu, X } from 'lucide-react';

/**
 * HandDrawnCameraIcon — Sketchy SVG camera with feTurbulence wobble.
 * Strokes turn orange when hasImage is true.
 */
const HandDrawnCameraIcon = ({ onClick, hasImage }) => (
    <div
        className="hand-drawn-camera-wrap"
        onClick={onClick}
        role="button"
        aria-label="Upload image"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && onClick()}
    >
        <svg
            width="28"
            height="28"
            viewBox="0 0 28 28"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            style={{ cursor: 'pointer' }}
        >
            {/* Hand-drawn camera body — slightly wobbly */}
            <path
                d="M3.5 9.2 C3.2 8.8 3.8 7.1 5.1 7.0 
                   L9.3 6.9 L10.8 4.8 C11.1 4.3 11.9 4.1 
                   12.4 4.2 L15.8 4.3 C16.4 4.2 17.1 4.5 
                   17.3 5.0 L18.7 7.1 L22.8 7.2 C24.2 7.3 
                   24.9 8.1 24.8 9.3 L24.6 19.8 C24.5 21.1 
                   23.5 21.9 22.2 21.8 L5.8 21.7 C4.4 21.8 
                   3.4 20.9 3.3 19.7 Z"
                stroke={hasImage ? '#f97316' : '#9ca3af'}
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
                style={{
                    filter: 'url(#sketchy)',
                    transition: 'stroke 0.2s'
                }}
            />
            {/* Lens — wobbly circle */}
            <path
                d="M14.1 9.5 C16.9 9.3 19.1 11.3 19.2 14.0 
                   C19.3 16.8 17.2 19.0 14.4 19.1 
                   C11.6 19.2 9.3 17.2 9.2 14.4 
                   C9.1 11.7 11.3 9.6 14.1 9.5 Z"
                stroke={hasImage ? '#f97316' : '#9ca3af'}
                strokeWidth="1.3"
                strokeLinecap="round"
                fill="none"
            />
            {/* Inner lens hint */}
            <path
                d="M14.0 11.8 C15.6 11.7 16.8 12.9 
                   16.9 14.4 C17.0 15.9 15.8 17.1 14.3 
                   17.2 C12.8 17.3 11.6 16.1 11.5 14.6 
                   C11.4 13.1 12.5 11.9 14.0 11.8 Z"
                stroke={hasImage ? '#f97316' : '#6b7280'}
                strokeWidth="0.9"
                strokeLinecap="round"
                fill={hasImage ? 'rgba(249,115,22,0.15)' : 'none'}
            />
            {/* Flash bump — wobbly */}
            <path
                d="M18.5 7.8 C18.4 7.1 18.9 6.4 19.8 6.3 
                   L21.5 6.4 C22.3 6.4 22.8 7.0 22.7 7.8 Z"
                stroke={hasImage ? '#f97316' : '#9ca3af'}
                strokeWidth="1.1"
                strokeLinecap="round"
                fill="none"
            />
            {/* Sketchy filter for roughness */}
            <defs>
                <filter id="sketchy" x="-5%" y="-5%"
                    width="110%" height="110%">
                    <feTurbulence
                        type="fractalNoise"
                        baseFrequency="0.04"
                        numOctaves="3"
                        result="noise"
                    />
                    <feDisplacementMap
                        in="SourceGraphic"
                        in2="noise"
                        scale="0.8"
                        xChannelSelector="R"
                        yChannelSelector="G"
                    />
                </filter>
            </defs>
        </svg>
    </div>
);

/**
 * ReasoningConsole - System-like query entry.
 * Replaces traditional chat bubbles with a command console feel.
 */
const ReasoningConsole = ({ onSend, isLoading, isMemoryActive, setInputValue: externalSetInputValue }) => {
    const [inputValue, setInputValue] = useState('');
    const [isSending, setIsSending] = useState(false);
    const [pendingImage, setPendingImage] = useState(null);
    const [imagePreview, setImagePreview] = useState(null);
    const textareaRef = useRef(null);
    const fileInputRef = useRef(null);

    // Expose input setter for external control (starter prompts)
    useEffect(() => {
        if (externalSetInputValue) {
            externalSetInputValue((text) => {
                setInputValue(text);
                setTimeout(() => textareaRef.current?.focus(), 100);
            });
        }
    }, [externalSetInputValue]);

    const handleSend = async () => {
        if (!inputValue.trim() || isLoading || isSending) return;

        setIsSending(true);
        onSend(inputValue.trim(), pendingImage);
        setInputValue('');
        setPendingImage(null);
        setImagePreview(null);

        setTimeout(() => setIsSending(false), 500);
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleImageSelect = (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setPendingImage(file);
        const reader = new FileReader();
        reader.onload = (ev) => setImagePreview(ev.target.result);
        reader.readAsDataURL(file);

        // Reset input so same file can be re-selected
        e.target.value = '';
    };

    const clearImage = () => {
        setPendingImage(null);
        setImagePreview(null);
    };

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
        }
    }, [inputValue]);

    return (
        <div className="p-3 md:p-6 bg-neutral-950/80 border-t border-neutral-800 backdrop-blur-none safe-bottom">
            <div className="max-w-4xl mx-auto flex flex-col gap-2 md:gap-3">
                {/* Meta Indicators */}
                <div className="flex items-center gap-3 md:gap-4 px-1">
                    <div className="flex items-center gap-1.5 grayscale opacity-50">
                        <Cpu className={`w-3 h-3 ${isLoading ? 'text-accent animate-pulse-subtle' : ''}`} />
                        <span className="text-[10px] font-mono uppercase tracking-widest hidden sm:inline">
                            Processor: {isLoading ? 'Active' : 'Idle'}
                        </span>
                        <span className="text-[10px] font-mono uppercase tracking-widest sm:hidden">
                            {isLoading ? 'Active' : 'Idle'}
                        </span>
                    </div>
                    <div className={`flex items-center gap-1.5 transition-opacity ${isMemoryActive ? 'opacity-50' : 'opacity-20'}`}>
                        <ShieldCheck className="w-3 h-3 text-accent" />
                        <span className="text-[10px] font-mono uppercase tracking-widest hidden sm:inline">
                            Memory: Contextual
                        </span>
                    </div>
                </div>

                {/* Image Preview Strip */}
                {imagePreview && (
                    <div className="flex items-center gap-2 px-1 animate-fade-in">
                        <div className="relative group/img">
                            <img
                                src={imagePreview}
                                alt="Pending upload"
                                className="w-16 h-16 object-cover rounded-lg border border-orange-500/30 ring-1 ring-orange-500/10"
                            />
                            <button
                                onClick={clearImage}
                                className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-neutral-900 border border-neutral-700 rounded-full flex items-center justify-center text-neutral-400 hover:text-red-400 hover:border-red-500/50 transition-colors opacity-0 group-hover/img:opacity-100"
                                aria-label="Remove image"
                            >
                                <X className="w-3 h-3" />
                            </button>
                        </div>
                        <span className="text-[10px] font-mono text-orange-400/60 uppercase tracking-wider">
                            Image attached
                        </span>
                    </div>
                )}

                {/* Input Surface */}
                <div className="relative group">
                    <div className="absolute inset-y-0 left-3 md:left-4 flex items-center pointer-events-none">
                        <Terminal className="w-4 h-4 text-neutral-600 group-focus-within:text-accent/50 transition-colors" />
                    </div>
                    <textarea
                        ref={textareaRef}
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={isLoading}
                        placeholder="Describe the dish, constraint, or scientific question..."
                        rows={1}
                        className={`w-full bg-neutral-900 border border-neutral-800 rounded-lg pl-10 md:pl-12 pr-24 md:pr-24 py-3 md:py-3.5 min-h-[48px] max-h-[200px] overflow-y-auto overflow-x-hidden text-sm md:text-base font-sans focus:outline-none focus:border-neutral-600 transition-all placeholder:text-neutral-600 resize-none leading-relaxed ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    />

                    {/* Action buttons — Camera + Send */}
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                        {/* Hidden file input */}
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            onChange={handleImageSelect}
                            className="hidden"
                            aria-hidden="true"
                        />

                        {/* Hand-drawn camera icon */}
                        <HandDrawnCameraIcon
                            onClick={() => fileInputRef.current?.click()}
                            hasImage={!!pendingImage}
                        />

                        {/* Send button */}
                        <button
                            onClick={handleSend}
                            disabled={!inputValue.trim() || isLoading || isSending}
                            className={`
                                min-w-[44px] min-h-[44px] flex items-center justify-center rounded-md transition-all active:scale-95
                                ${!inputValue.trim() || isLoading || isSending
                                    ? 'text-neutral-700'
                                    : 'text-accent hover:bg-accent/10'}
                            `}
                        >
                            <Send className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            </div>

            {/* Hover animation for camera icon */}
            <style>{`
                .hand-drawn-camera-wrap {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-width: 36px;
                    min-height: 36px;
                    border-radius: 6px;
                    transition: background 0.15s;
                }
                .hand-drawn-camera-wrap:hover {
                    background: rgba(249, 115, 22, 0.06);
                }
                .hand-drawn-camera-wrap:hover svg {
                    transform: scale(1.1) rotate(-2deg);
                    transition: transform 0.15s ease;
                }
                .hand-drawn-camera-wrap svg {
                    transition: transform 0.15s ease;
                }
            `}</style>
        </div>
    );
};

export default ReasoningConsole;

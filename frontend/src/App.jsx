
import { useState, useEffect, useRef } from 'react';
import { streamNutriChat, getSessionId, clearSession, getConversation, getConversationsList, createNewSession, getPerformanceMode } from './api/apiClient';


import SystemStatus from './components/SystemStatus';
import ReasoningConsole from './components/ReasoningConsole';
import PhaseStream from './components/PhaseStream';
import ErrorBoundary from './components/ErrorBoundary';
import Sidebar from './components/Sidebar';
import ChatHeader from './components/ChatHeader';

// Input value setter for starter prompts
let inputValueSetter = null;

function App() {
    const [messages, setMessages] = useState([]);

    // State Machine: 'IDLE' | 'HYDRATING' | 'STREAMING' | 'DONE' | 'ERROR'
    const [streamStatus, setStreamStatus] = useState('HYDRATING'); // Start hydrating


    const [sessionId, setSessionId] = useState('');
    const [conversations, setConversations] = useState([]);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    const [turnCount, setTurnCount] = useState(0);
    const [memoryScope, setMemoryScope] = useState('new'); // 'new', 'session', 'decayed'
    const [performanceMode, setPerformanceMode] = useState(false);


    const abortRef = useRef(null);
    const timeoutRef = useRef(null);

    // Initial Load: Fetch List & Hydrate Most Recent
    useEffect(() => {
        const init = async () => {
            setStreamStatus('HYDRATING');
            try {
                // 1. Get List
                const list = await getConversationsList();
                setConversations(list);

                let targetSid = getSessionId();

                // 2. Decide Session ID
                if (!targetSid && list.length > 0) {
                    // Auto-select most recent
                    targetSid = list[0].session_id;
                    localStorage.setItem('nutri_session_id', targetSid);
                } else if (!targetSid) {
                    // Create new if truly nothing
                    targetSid = await createNewSession();
                }

                setSessionId(targetSid);
                await hydrateSession(targetSid);

                // 3. Set Performance Mode
                setPerformanceMode(getPerformanceMode());


            } catch (e) {
                console.error('Init failed:', e);
                setStreamStatus('IDLE');
            }
        };
        init();
    }, []);

    // Helper: Hydrate a specific session
    const hydrateSession = async (sid) => {
        setStreamStatus('HYDRATING');
        setMessages([]); // Clear UI immediately
        try {
            const data = await getConversation(sid);

            if (data.messages && data.messages.length > 0) {
                setMessages(data.messages.map((m, i) => ({
                    ...m,
                    id: `hist - ${i} `,
                    isStreaming: false
                })));
                setTurnCount(data.messages.filter(m => m.role === 'user').length);
                setMemoryScope('session');

                if (data.current_mode) {
                    console.log(`[HYDRATE] Resuming in mode: ${data.current_mode} `);
                }
            } else {
                setMessages([]);
                setTurnCount(0);
                setMemoryScope('new');
            }
        } catch (e) {
            console.error('[HYDRATE] Failed to hydrate:', e);
            // Show error in logs but allow user to try typing
        } finally {
            setStreamStatus('IDLE');
        }
    };

    const handleSwitchSession = async (sid) => {
        if (streamStatus === 'STREAMING') return; // Prevent switch during stream
        if (sid === sessionId) return;

        setSessionId(sid);
        localStorage.setItem('nutri_session_id', sid);
        await hydrateSession(sid);
        setIsSidebarOpen(false); // Close sidebar after switching
    };

    const handleNewChat = async () => {
        if (streamStatus === 'STREAMING') return;

        const newSid = await createNewSession();
        setSessionId(newSid);

        // Optimistic update of list (will be empty/new entry)
        const newConv = { session_id: newSid, title: 'New Conversation', last_active: new Date().toISOString(), preview: 'Ready to start' };
        setConversations(prev => [newConv, ...prev]);

        await hydrateSession(newSid);
        setIsSidebarOpen(false);
    };

    const cleanupStream = (finalStatus = 'IDLE') => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        setStreamStatus(finalStatus);
    };

    const handleSend = async (query) => {
        // Circuit Breaker: Force-stop any existing stream
        if (abortRef.current) {
            console.warn('[CIRCUIT BREAKER] Aborting previous stream.');
            abortRef.current();
            abortRef.current = null;
        }

        // Reset to IDLE briefly to ensure clean slate (React 18 automatic batching handles this,
        // but explicit ordering helps logic clarity)
        cleanupStream('IDLE');

        setStreamStatus('STREAMING');
        setTurnCount(prev => prev + 1);

        // Add user query
        setMessages(prev => [...prev, { role: 'user', content: query, id: Date.now() + '-user' }]);

        // Add assistant placeholder
        const assistantId = Date.now() + '-assistant';
        setMessages(prev => [...prev, {
            id: assistantId,
            role: 'assistant',
            content: '',
            phases: [],
            isStreaming: true,
            statusMessage: ''
        }]);

        // Failsafe: 180s max dead-stream duration
        const FAILSAFE_TIMEOUT = 180000;
        const resetFailsafe = () => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            timeoutRef.current = setTimeout(() => {
                console.warn('[SSE] Failsafe timeout — forcing unlock');
                if (abortRef.current) abortRef.current();

                setMessages(prev => prev.map(m =>
                    m.id === assistantId
                        ? { ...m, isStreaming: false, statusMessage: 'Connection timed out.' }
                        : m
                ));
                cleanupStream('IDLE');
            }, FAILSAFE_TIMEOUT);
        };

        resetFailsafe();

        abortRef.current = streamNutriChat(
            query,
            {
                verbosity: 'standard', // Hardcoded default as ControlRail is removed
                explanations: true,
                streaming: true,
                execution_mode: null
            },
            // onReasoning
            (phaseMessage) => {
                resetFailsafe();
                setMessages(prev => prev.map(m =>
                    m.id === assistantId
                        ? { ...m, statusMessage: phaseMessage }
                        : m
                ));
            },
            // onToken
            (token) => {
                resetFailsafe();
                setMessages(prev => prev.map(m =>
                    m.id === assistantId
                        ? { ...m, content: m.content + token }
                        : m
                ));
            },
            // onComplete
            (statusData) => {
                console.log(`[SSE] Completed logically via [DONE] with status: ${statusData?.status}`);

                setMessages(prev => {
                    const updated = prev.map(m => {
                        if (m.id === assistantId) {
                            // Empty Stream Logic
                            if (!m.content || m.content.trim() === '') {
                                return {
                                    ...m,
                                    isStreaming: false,
                                    statusMessage: 'Response was empty. (Hint: Try a simpler query)'
                                };
                            }
                            return {
                                ...m,
                                isStreaming: false,
                                statusMessage: statusData?.status === 'error' ? `Error: ${statusData.message}` : ''
                            };
                        }
                        return m;
                    });

                    // One-time identity footer after first assistant response
                    let isFirstResponse = false;
                    try {
                        isFirstResponse = !sessionStorage.getItem('nutri_identity_footer_shown');
                        if (isFirstResponse) {
                            sessionStorage.setItem('nutri_identity_footer_shown', 'true');
                        }
                    } catch (e) {
                        console.warn('[STORAGE] sessionStorage inaccessible:', e);
                    }

                    if (isFirstResponse) {
                        return [
                            ...updated,
                            {
                                id: Date.now() + '-identity-footer',
                                role: 'system',
                                content: 'Nutri answers by modeling cooking as a physical system.'
                            }
                        ];
                    }

                    return updated;
                });

                // Transition to IDLE immediately to unlock input
                setStreamStatus('IDLE');
                setMemoryScope('session');

                if (timeoutRef.current) clearTimeout(timeoutRef.current);
            },
            // onError
            (err) => {
                console.error('[SSE] Error detected:', err);
                setMessages(prev => prev.map(m =>
                    m.id === assistantId
                        ? { ...m, content: m.content + `\n\n[System Error: ${err.message}]`, isStreaming: false }
                        : m
                ));
                cleanupStream('IDLE'); // Unlock even on error
            },
            // onStatus
            (statusData) => {
                resetFailsafe();
                if (!statusData) return;
                const { phase, message } = statusData;
                if (phase === 'reset') {
                    setMemoryScope('decayed');
                    setMessages(prev => [
                        ...prev,
                        {
                            id: Date.now() + '-sys',
                            role: 'system',
                            content: 'Session expired due to inactivity. Memory has been reset.'
                        }
                    ]);
                    setTurnCount(0);
                }
                setMessages(prev => prev.map(m =>
                    m.id === assistantId
                        ? { ...m, statusMessage: message || phase }
                        : m
                ));
            },
            // onNutritionReport
            (report) => {
                resetFailsafe();
                setMessages(prev => prev.map(m =>
                    m.id === assistantId
                        ? { ...m, nutritionVerification: report }
                        : m
                ));
            },
            // onTrace
            (trace) => {
                resetFailsafe();
                setMessages(prev => prev.map(m =>
                    m.id === assistantId
                        ? { ...m, executionTrace: trace }
                        : m
                ));
            }
        );
    };

    const handleNewSession = () => {
        clearSession();
        const sid = getSessionId();
        setSessionId(sid);
        setMessages([]);
        setTurnCount(0);
        setStreamStatus('IDLE');
        setMemoryScope('new');
    };

    return (
        <ErrorBoundary>
            <div className="flex h-screen w-screen bg-neutral-950 text-neutral-100 font-sans overflow-hidden selection:bg-accent/30">

                {/* 1. Sidebar (Persistent on Desktop, Drawer on Mobile) */}
                <Sidebar
                    isOpen={isSidebarOpen}
                    setIsOpen={setIsSidebarOpen}
                    conversations={conversations}
                    currentSessionId={sessionId}
                    onSelectSession={handleSwitchSession}
                    onNewChat={handleNewChat}
                />

                {/* Main Content Area */}
                <div className="flex-1 flex flex-col h-full bg-neutral-900/20 relative">

                    {/* 2. Chat Header (Fixed Top) */}
                    <ChatHeader
                        title={conversations.find(c => c.session_id === sessionId)?.title}
                        lastActive={conversations.find(c => c.session_id === sessionId)?.last_active}
                        onOpenSidebar={() => setIsSidebarOpen(true)}
                    />

                    {/* System Telemetry - Top (Just below header) */}
                    <div className="mt-16 relative">
                        <SystemStatus
                            sessionId={sessionId}
                            turnCount={turnCount}
                        />

                        {performanceMode && (
                            <div className="absolute top-2 right-4 flex items-center gap-1.5 px-2 py-0.5 bg-amber-500/10 border border-amber-500/20 rounded-md text-[9px] font-mono text-amber-500 animate-pulse uppercase tracking-wider">
                                <span className="w-1 h-1 bg-amber-500 rounded-full"></span>
                                Performance Mode Active
                            </div>
                        )}
                    </div>


                    {/* Reasoning Stream - Scrollable */}
                    <PhaseStream
                        messages={messages}
                        streamStatus={streamStatus}
                        onPromptSelect={(text) => {
                            if (inputValueSetter) inputValueSetter(text);
                        }}
                    />

                    {/* Reasoning Console - Bottom */}
                    <ReasoningConsole
                        onSend={handleSend}
                        isLoading={streamStatus === 'STREAMING' || streamStatus === 'HYDRATING'}
                        isMemoryActive={memoryScope === 'session' || turnCount > 0}
                        setInputValue={(setter) => { inputValueSetter = setter; }}
                    />

                    {/* Memory Transparency Signal */}
                    {memoryScope === 'session' && messages.length > 0 && streamStatus === 'IDLE' && (
                        <div className="absolute bottom-24 left-1/2 -translate-x-1/2 bg-neutral-900/80 border border-neutral-800 px-3 py-1 rounded-full text-[9px] font-mono uppercase tracking-widest text-neutral-500 animate-fade-in pointer-events-none z-10">
                            Nutri remembers this conversation
                        </div>
                    )}
                </div>

                {/* Control Rail - REMOVED (Dead Code) */}
            </div>
        </ErrorBoundary>
    );
}

export default App;
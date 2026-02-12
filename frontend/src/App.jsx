
import { useState, useEffect, useRef, useCallback } from 'react';
import { streamNutriChat, getSessionId, clearSession, getConversation, getConversationsList, createNewSession, getPerformanceMode, getHealth } from './api/apiClient';


import SystemStatus from './components/SystemStatus';
import ReasoningConsole from './components/ReasoningConsole';
import PhaseStream from './components/PhaseStream';
import ErrorBoundary from './components/ErrorBoundary';
import Sidebar from './components/Sidebar';
import ChatHeader from './components/ChatHeader';

// Input value setter for starter prompts
let inputValueSetter = null;
function App() {
    useEffect(() => {
        console.log("%c NUTRI SYSTEM %c Build ID: " + import.meta.env.VITE_GIT_SHA, "background: #22c55e; color: white; font-weight: bold; padding: 2px 4px; border-radius: 4px;", "color: #22c55e; font-weight: bold;");
    }, []);

    const [messages, setMessages] = useState([]);

    // State Machine: 'IDLE' | 'HYDRATING' | 'STREAMING' | 'DONE' | 'ERROR'
    const [streamStatus, setStreamStatus] = useState('HYDRATING'); // Start hydrating


    const [sessionId, setSessionId] = useState('');
    const [conversations, setConversations] = useState([]);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    const [turnCount, setTurnCount] = useState(0);
    const [memoryScope, setMemoryScope] = useState('new'); // 'new', 'session', 'decayed'
    const [performanceMode, setPerformanceMode] = useState(false);
    const [backendStatus, setBackendStatus] = useState('unknown'); // 'unknown' | 'ok' | 'fail'
    const [activeRunId, setActiveRunId] = useState(null);
    const [activePipeline, setActivePipeline] = useState(null);

    /**
     * updateMessageTrace - Centralized Single Writer for Scientific Traces.
     * Enforces monotonic guard and provides source attribution.
     */
    const updateMessageTrace = useCallback((targetId, trace, source, seq = 0) => {
        if (!trace) return;

        console.log(`%c [TRACE_WRITE_ATTEMPT] from=${source} seq=${seq} `, "color: #3b82f6; font-weight: bold;");

        setMessages(prev => prev.map(m => {
            if (m.id !== targetId) return m;

            const currentSeq = m._lastTraceSeq || 0;

            // MONOTONIC GUARD: Incoming sequence must be >= current
            if (m.executionTrace && seq < currentSeq) {
                console.log(`%c [TRACE_GUARD] blocked from=${source} (seq=${seq} < curr=${currentSeq}) `, "color: #ef4444; font-weight: bold;");
                return m;
            }

            console.log(`%c [STATE_WRITE] from=${source} seq=${seq} claims=${trace.claims?.length || 0} accepted=true `, "color: #10b981; font-weight: bold;");

            return {
                ...m,
                executionTrace: trace,
                _lastTraceSeq: seq
            };
        }));
    }, []);

    const abortRef = useRef(null);
    const timeoutRef = useRef(null);
    const stallTimeoutRef = useRef(null);

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
                    // Lazy Load: Do NOT create session yet.
                    targetSid = null;
                    clearSession();
                }

                setSessionId(targetSid);
                await hydrateSession(targetSid);

                // 3. Set Performance Mode
                const health = await getHealth();
                if (health.status === 'offline' || health.status === 'error') {
                    console.error('%c [CONNECTIVITY] FAIL: Backend unreachable ', "background: #ef4444; color: white; font-weight: bold;");
                    setBackendStatus('fail');
                } else {
                    console.log('%c [CONNECTIVITY] OK ', "background: #10b981; color: white; font-weight: bold;");
                    setBackendStatus('ok');
                }

                setPerformanceMode(getPerformanceMode());


            } catch (e) {
                console.error('Init failed:', e);
                setBackendStatus('fail');
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
                // Step 7: Hydration MUST preserve execution_trace from API
                setMessages(data.messages.map((m, i) => {
                    // API returns snake_case, UI uses camelCase
                    const trace = m.executionTrace || m.execution_trace || null;
                    if (trace) {
                        console.log(`%c [TRACE_WRITE_ATTEMPT] from=HYDRATION seq=0 `, "color: #3b82f6; font-weight: bold;");
                    }
                    return {
                        ...m,
                        id: `hist-${i}`,
                        isStreaming: false,
                        executionTrace: trace,
                        _lastTraceSeq: 0 // Reset sequence for historical data
                    };
                }));
                setTurnCount(data.messages.filter(m => m.role === 'user').length);
                setMemoryScope('session');

                if (data.current_mode) {
                    console.log(`[HYDRATE] Resuming in mode: ${data.current_mode}`);
                }
            } else {
                setMessages([]);
                setTurnCount(0);
                setMemoryScope('new');
            }
        } catch (e) {
            console.error('[HYDRATE] Failed to hydrate:', e);
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

        // Lazy: Just clear state
        clearSession();
        setSessionId(null);
        setMessages([]);
        setTurnCount(0);
        setMemoryScope('new');

        setIsSidebarOpen(false);
    };

    const cleanupStream = (finalStatus = 'IDLE') => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        if (stallTimeoutRef.current) clearTimeout(stallTimeoutRef.current);
        setStreamStatus(finalStatus);
    };

    const handleSend = async (query) => {
        // JIT Session Creation
        let currentSid = sessionId;
        if (!currentSid) {
            // Generate client-side ID immediately
            currentSid = getSessionId(); // This updates localStorage
            setSessionId(currentSid);

            // Add to list optimistically
            const newConv = {
                session_id: currentSid,
                title: query.slice(0, 30) + (query.length > 30 ? '...' : ''),
                last_active: new Date().toISOString(),
                preview: 'Just now'
            };
            setConversations(prev => [newConv, ...prev]);
        }

        // Circuit Breaker: Force-stop any existing stream
        if (abortRef.current) {
            console.warn('[CIRCUIT BREAKER] Aborting previous stream.');
            abortRef.current();
            abortRef.current = null;
        }

        // Reset to IDLE briefly to ensure clean slate (React 18 automatic batching handles this,
        // but explicit ordering helps logic clarity)
        cleanupStream('IDLE');

        const newRunId = crypto.randomUUID();
        const pipeline = "flavor_explainer"; // Default pipeline
        setActiveRunId(newRunId);
        setActivePipeline(pipeline);

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

        // Stall Indicator: 10s of silence after last activity
        const STALL_TIMEOUT = 10000;
        const resetStallIndicator = () => {
            if (stallTimeoutRef.current) clearTimeout(stallTimeoutRef.current);
            stallTimeoutRef.current = setTimeout(() => {
                if (streamStatus === 'STREAMING') {
                    console.warn('[SSE] Stream stalled — no activity for 10s');
                    setMessages(prev => prev.map(m =>
                        m.id === assistantId
                            ? { ...m, statusMessage: 'Stream stalled — retrying...' }
                            : m
                    ));
                }
            }, STALL_TIMEOUT);
        };

        resetFailsafe();
        resetStallIndicator();

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
                resetStallIndicator();
                setMessages(prev => prev.map(m =>
                    m.id === assistantId
                        ? { ...m, statusMessage: phaseMessage }
                        : m
                ));
            },
            // onToken
            (token) => {
                resetFailsafe();
                resetStallIndicator();
                setMessages(prev => prev.map(m =>
                    m.id === assistantId
                        ? { ...m, content: m.content + token }
                        : m
                ));
            },
            // onComplete — Step 2: MERGE, never replace
            (statusData) => {
                console.log(`[SSE] Completed logically via [DONE] with status: ${statusData?.status}`);

                setMessages(prev => {
                    const updated = prev.map(m => {
                        if (m.id === assistantId) {
                            // Step 5: Nuclear debug — catch trace deletion
                            if (m.executionTrace) {
                                console.log(`[TRACE_AUDIT] DONE handler: preserving ${m.executionTrace.claims?.length || 0} claims`);
                            }

                            // Step 2: Explicitly preserve executionTrace using the single writer logic
                            const preserved = {
                                ...m,
                                isStreaming: false,
                                statusMessage: (!m.content || m.content.trim() === '')
                                    ? 'Response was empty. (Hint: Try a simpler query)'
                                    : (statusData?.status === 'error' ? `Error: ${statusData.message}` : '')
                            };

                            // Double Check: Ensure we didn't drop the trace
                            if (m.executionTrace && !preserved.executionTrace) {
                                preserved.executionTrace = m.executionTrace;
                            }

                            return preserved;
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
                if (stallTimeoutRef.current) clearTimeout(stallTimeoutRef.current);
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
            (statusData) => {
                if (!statusData) return;

                // Border Control
                if (statusData.run_id && statusData.run_id !== newRunId) {
                    console.warn(`[RUN_GUARD] Rejected foreign status from ${statusData.run_id}`);
                    return;
                }

                resetFailsafe();
                resetStallIndicator();

                const { phase, message } = statusData.content || statusData;
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
                // Border Control
                if (report.run_id && report.run_id !== newRunId) {
                    console.warn(`[RUN_GUARD] Rejected foreign report from ${report.run_id}`);
                    return;
                }

                resetFailsafe();
                resetStallIndicator();
                setMessages(prev => prev.map(m =>
                    m.id === assistantId
                        ? { ...m, nutritionVerification: report }
                        : m
                ));
            },
            // onTrace — Funnel through Single Writer
            (tracePacket) => {
                const incomingRunId = tracePacket.run_id || (tracePacket.content && tracePacket.content.run_id);
                const incomingPipeline = tracePacket.pipeline || (tracePacket.content && tracePacket.content.pipeline);

                // Border Control: No warnings. No merging. No forgiveness.
                if (incomingRunId && incomingRunId !== newRunId) {
                    console.warn(`[RUN_GUARD] REJECTED: run=${incomingRunId} (expected ${newRunId})`);
                    return;
                }
                if (incomingPipeline && incomingPipeline !== pipeline) {
                    console.warn(`[PIPELINE_GUARD] REJECTED: pipeline=${incomingPipeline} (expected ${pipeline})`);
                    return;
                }

                resetFailsafe();
                resetStallIndicator();

                const trace = tracePacket.content || tracePacket;
                const incomingSeq = tracePacket.seq || trace.seq || 0;

                updateMessageTrace(assistantId, trace, "SSE", incomingSeq);
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

                    {/* Infrastructure Failure Banner */}
                    {backendStatus === 'fail' && (
                        <div className="absolute top-0 left-0 right-0 z-50 bg-red-600/90 backdrop-blur-md border-b border-red-500 py-3 px-6 flex items-center justify-between animate-slide-down">
                            <div className="flex items-center gap-3">
                                <div className="w-2 h-2 bg-white rounded-full animate-ping"></div>
                                <span className="text-sm font-bold tracking-tight text-white uppercase">
                                    Backend unreachable – claims cannot arrive.
                                </span>
                            </div>
                            <button
                                onClick={() => window.location.reload()}
                                className="px-3 py-1 bg-white/20 hover:bg-white/30 rounded text-[10px] font-bold text-white uppercase transition-colors"
                            >
                                Retry Connection
                            </button>
                        </div>
                    )}

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
                    <div className="absolute bottom-24 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 pointer-events-none z-10">
                        <div className="bg-neutral-900/80 border border-neutral-800 px-3 py-1 rounded-full text-[9px] font-mono uppercase tracking-widest text-neutral-500 animate-fade-in">
                            Nutri remembers this conversation
                        </div>
                        <div className="text-[8px] font-mono text-neutral-700 opacity-50">
                            Build: {import.meta.env.VITE_GIT_SHA}
                        </div>
                    </div>
                </div>

                {/* Control Rail - REMOVED (Dead Code) */}
            </div>
        </ErrorBoundary>
    );
}

export default App;
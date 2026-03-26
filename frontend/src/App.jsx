
import { useState, useEffect, useRef, useCallback } from 'react';
import { 
  streamNutriChat, 
  getSessionId, 
  clearSession, 
  getConversation, 
  getConversationsList, 
  createNewSession, 
  getPerformanceMode, 
  getHealth,
  getPreferences,
  updatePreferences
} from './api/apiClient';
import { saveMessages, loadMessages, clearMessages } from './utils/chatStorage';


import SystemStatus from './components/SystemStatus';
import ReasoningConsole from './components/ReasoningConsole';
import PhaseStream from './components/PhaseStream';
import ErrorBoundary from './components/ErrorBoundary';
import Sidebar from './components/Sidebar';
import ChatHeader from './components/ChatHeader';
import PreferencesModal from './components/PreferencesModal';

// Input value setter for starter prompts
let inputValueSetter = null;
function App() {
    useEffect(() => {
        console.log("%c NUTRI SYSTEM %c Build ID: " + import.meta.env.VITE_GIT_SHA, "background: #22c55e; color: white; font-weight: bold; padding: 2px 4px; border-radius: 4px;", "color: #22c55e; font-weight: bold;");
    }, []);

    const [messages, setMessages] = useState(() => loadMessages());

    // Autosave messages to localStorage whenever they change
    useEffect(() => {
        saveMessages(messages);
    }, [messages]);

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

    // Personalization & Onboarding
    const [userPreferences, setUserPreferences] = useState(null);
    const [isPreferencesOpen, setIsPreferencesOpen] = useState(false);

    // Memory Insights (STC-005)
    const [memoryInsight, setMemoryInsight] = useState(null);

    // Fetch preferences on load
    useEffect(() => {
        const fetchPrefs = async () => {
            const prefs = await getPreferences();
            if (prefs) {
                setUserPreferences(prefs);
                // Onboarding: if skill_level is missing, open modal
                if (!prefs.skill_level) {
                    setIsPreferencesOpen(true);
                }
            } else {
                // Fallback: open onboarding if fetch fails or no prefs
                setIsPreferencesOpen(true);
            }
        };
        fetchPrefs();
    }, []);

    const handleUpdatePreferences = async (newPrefs) => {
        try {
            await updatePreferences(newPrefs);
            setUserPreferences(newPrefs);
        } catch (error) {
            console.error("Failed to update preferences:", error);
        }
    };

    /**
     * updateMessageTrace - Centralized Single Writer for Scientific Traces.
     * Enforces monotonic guard and provides source attribution.
     */
    const updateMessageTrace = useCallback((targetId, trace, source, seq = 0) => {
        if (!trace) return;

        // TELEMETRY: STATE UPDATE
        console.log("🧠 [POINT 3: STATE STORE] REACT STATE TRACE", { trace, source, seq });

        setMessages(prev => prev.map(m => {
            if (m.id !== targetId) return m;

            const currentSeq = m._lastTraceSeq || 0;

            if (m.executionTrace && seq < currentSeq) {
                return m;
            }

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
    const isHydratingRef = useRef(false);

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
        if (!sid) {
            setStreamStatus('IDLE');
            return;
        }

        if (isHydratingRef.current) return;
        isHydratingRef.current = true;

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

                // Update title in conversations list from hydrated data
                if (data.title && data.title !== 'New Conversation') {
                    setConversations(prev => prev.map(c =>
                        c.session_id === sid ? { ...c, title: data.title } : c
                    ));
                }

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
            if (e.status === 403) {
                console.warn("⚠️ [AUTH] Session 403: Stale identity detected. Clearing session...");
                clearSession();
                setSessionId(null);
                setMessages([]);
                setTurnCount(0);

                // Nuclear URL Cleanup: Remove ?session_id=... to prevent reload loops
                if (window.location.search.includes('session_id')) {
                    const url = new URL(window.location);
                    url.searchParams.delete('session_id');
                    window.history.replaceState({}, document.title, url.pathname + url.search);
                }

                setStreamStatus('DONE'); // Unlock UI to show landing screen
            } else {
                setStreamStatus('ERROR');
            }
        } finally {
            isHydratingRef.current = false;
            // Only set IDLE if we didn't just 403-reset
            setStreamStatus(prev => prev === 'HYDRATING' ? 'IDLE' : prev);
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
        clearMessages();
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

    const handleSend = async (query, imageFile = null) => {
        let imageData = null;

        // 📸 [VISION SIDECAR] Prepare image if present
        if (imageFile) {
            imageData = await new Promise((resolve) => {
                const reader = new FileReader();
                reader.onload = (e) => resolve({
                    b64: e.target.result,
                    media_type: imageFile.type
                });
                reader.readAsDataURL(imageFile);
            });
        }

        // JIT Session Creation
        let currentSid = sessionId;
        if (!currentSid) {
            currentSid = getSessionId();
            setSessionId(currentSid);
            const newConv = {
                session_id: currentSid,
                title: query.slice(0, 30) + (query.length > 30 ? '...' : ''),
                last_active: new Date().toISOString(),
                preview: 'Just now'
            };
            setConversations(prev => [newConv, ...prev]);
        }

        if (abortRef.current) {
            abortRef.current();
            abortRef.current = null;
        }

        cleanupStream('STREAMING');
        setMemoryInsight(null);
        setTurnCount(prev => prev + 1);

        const newRunId = crypto.randomUUID();
        let detectedPipeline = null;
        setActiveRunId(newRunId);
        setActivePipeline(null);

        // Add user query with optional image
        setMessages(prev => [...prev, { 
            role: 'user', 
            content: query, 
            id: Date.now() + '-user',
            image: imageData?.b64
        }]);

        const assistantId = Date.now() + '-assistant';
        setMessages(prev => [...prev, {
            id: assistantId,
            role: 'assistant',
            content: '',
            phases: [],
            isStreaming: true,
            statusMessage: ''
        }]);

        const FAILSAFE_TIMEOUT = 180000;
        const resetFailsafe = () => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            timeoutRef.current = setTimeout(() => {
                if (abortRef.current) abortRef.current();
                setMessages(prev => prev.map(m =>
                    m.id === assistantId ? { ...m, isStreaming: false, statusMessage: 'Connection timed out.' } : m
                ));
                cleanupStream('IDLE');
            }, FAILSAFE_TIMEOUT);
        };

        const STALL_TIMEOUT = 10000;
        const resetStallIndicator = () => {
            if (stallTimeoutRef.current) clearTimeout(stallTimeoutRef.current);
            stallTimeoutRef.current = setTimeout(() => {
                if (streamStatus === 'STREAMING') {
                    setMessages(prev => prev.map(m =>
                        m.id === assistantId ? { ...m, statusMessage: 'Stream stalled — retrying...' } : m
                    ));
                }
            }, STALL_TIMEOUT);
        };

        resetFailsafe();
        resetStallIndicator();

        const onToken = (token) => {
            resetFailsafe();
            resetStallIndicator();
            setMessages(prev => prev.map(m =>
                m.id === assistantId ? { ...m, content: (m.content || '') + token } : m
            ));
        };

        const onComplete = (statusData) => {
            setMessages(prev => {
                const updated = prev.map(m => {
                    if (m.id === assistantId) {
                        return {
                            ...m,
                            isStreaming: false,
                            statusMessage: (!m.content || m.content.trim() === '')
                                ? 'Response was empty. (Hint: Try a simpler query)'
                                : (statusData?.status === 'error' ? `Error: ${statusData.message}` : '')
                        };
                    }
                    return m;
                });

                let isFirstResponse = false;
                try {
                    isFirstResponse = !sessionStorage.getItem('nutri_identity_footer_shown');
                    if (isFirstResponse) sessionStorage.setItem('nutri_identity_footer_shown', 'true');
                } catch (e) {}

                if (isFirstResponse) {
                    return [...updated, { id: Date.now() + '-identity-footer', role: 'system', content: 'Nutri answers by modeling cooking as a physical system.' }];
                }
                return updated;
            });

            setStreamStatus('IDLE');
            setMemoryScope('session');
            getConversationsList().then(list => { if (list?.length) setConversations(list); }).catch(() => {});
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            if (stallTimeoutRef.current) clearTimeout(stallTimeoutRef.current);
        };

        const onError = (err) => {
            setMessages(prev => prev.map(m =>
                m.id === assistantId ? { ...m, content: (m.content || '') + `\n\n[System Error: ${err.message}]`, isStreaming: false } : m
            ));
            cleanupStream('IDLE');
        };

        const onStatus = (statusData) => {
            if (!statusData || (statusData.run_id && statusData.run_id !== newRunId)) return;
            resetFailsafe();
            resetStallIndicator();
            const { phase, message } = statusData.content || statusData;
            setMessages(prev => prev.map(m =>
                m.id === assistantId ? { ...m, statusMessage: message || phase } : m
            ));
        };

        const onNutritionReport = (report) => {
            if (report.run_id && report.run_id !== newRunId) return;
            resetFailsafe();
            resetStallIndicator();
            setMessages(prev => prev.map(m =>
                m.id === assistantId ? { ...m, nutritionVerification: report } : m
            ));
        };

        const onTrace = (tracePacket) => {
            const incomingRunId = tracePacket.run_id || (tracePacket.content && tracePacket.content.run_id);
            const incomingPipeline = tracePacket.pipeline || (tracePacket.content && tracePacket.content.pipeline);
            
            if (incomingRunId && incomingRunId !== newRunId) return;
            
            if (incomingPipeline) {
                if (!detectedPipeline) {
                    detectedPipeline = incomingPipeline;
                    setActivePipeline(incomingPipeline);
                }
            }

            resetFailsafe();
            resetStallIndicator();
            const trace = tracePacket.content || tracePacket;
            const incomingSeq = tracePacket.seq || trace.seq || 0;
            updateMessageTrace(assistantId, trace, "SSE", incomingSeq);
        };

        const onMemoryInsight = (insight) => {
            setMemoryInsight(insight);
        };

        const onAdversarialCritique = (critique) => {
            if (critique.run_id && critique.run_id !== newRunId) return;
            resetFailsafe();
            resetStallIndicator();
            setMessages(prev => prev.map(m => {
                if (m.id !== assistantId) return m;
                return {
                    ...m,
                    executionTrace: {
                        ...(m.executionTrace || {}),
                        adversarial_critique: critique
                    }
                };
            }));
        };

        abortRef.current = streamNutriChat(
            query,
            {
                audience_mode: userPreferences.audience_mode,
                optimization_goal: userPreferences.optimization_goal,
                verbosity: userPreferences.verbosity,
                execution_mode: userPreferences.execution_mode,
                run_id: newRunId
            },
            onStatus, // onReasoning (status events also serve as reasoning indicators)
            onToken,
            onComplete,
            onError,
            onStatus,
            onNutritionReport,
            onTrace,
            onMemoryInsight,
            onAdversarialCritique,
            imageData
        );
    };

    const handleNewSession = () => {
        clearSession();
        clearMessages();
        const sid = getSessionId();
        setSessionId(sid);
        setMessages([]);
        setTurnCount(0);
        setStreamStatus('IDLE');
        setMemoryScope('new');
        setMemoryInsight(null);
    };

    return (
        <ErrorBoundary>
            <div className="app-root h-screen w-screen bg-neutral-950 text-neutral-100 font-sans flex flex-col overflow-hidden selection:bg-accent/30 relative">

                {/* 1. Sidebar (Persistent on Desktop, Drawer on Mobile) */}
                <Sidebar
                    isOpen={isSidebarOpen}
                    setIsOpen={setIsSidebarOpen}
                    conversations={conversations}
                    currentSessionId={sessionId}
                    onSelectSession={(sid) => {
                        handleSwitchSession(sid);
                        setIsSidebarOpen(false);
                    }}
                    onNewChat={() => {
                        handleNewChat();
                        setIsSidebarOpen(false);
                    }}
                    onOpenPreferences={() => setIsPreferencesOpen(true)}
                />

                {/* Main Content Area */}
                <div className="w-full h-full bg-neutral-900/20 flex flex-col relative">

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
                    <div className="relative shrink-0">
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

                    {/* Chat Layout Wrapper */}
                    <div className="chat-wrapper">
                        {/* Memory Transparency Signal (In-flow banner) */}
                        <div className="shrink-0 flex flex-col items-center justify-center gap-1 py-3 z-10 w-full">
                            <div className="bg-neutral-900/80 border border-neutral-800 px-3 py-1 rounded-full text-[9px] font-mono uppercase tracking-widest text-neutral-500 animate-fade-in">
                                Nutri remembers this conversation
                            </div>
                            <div className="text-[8px] font-mono text-neutral-700 opacity-50">
                                Build: {import.meta.env.VITE_GIT_SHA}
                            </div>
                        </div>

                        {/* Scrollable Conversation Stream */}
                        <PhaseStream
                            messages={messages}
                            streamStatus={streamStatus}
                            memoryInsight={memoryInsight}
                            onDismissInsight={() => setMemoryInsight(null)}
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
                    </div>
                </div>
                {/* Preferences & Onboarding Modal */}
                <PreferencesModal 
                    isOpen={isPreferencesOpen} 
                    onClose={() => setIsPreferencesOpen(false)} 
                    onSave={handleUpdatePreferences}
                    initialData={userPreferences}
                />
            </div>
        </ErrorBoundary>
    );
}

export default App;
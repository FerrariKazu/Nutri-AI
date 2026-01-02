import { useState, useEffect, useRef } from 'react';
import { streamNutriChat, getSessionId, clearSession } from './api/apiClient';
import ControlRail from './components/ControlRail';
import SystemStatus from './components/SystemStatus';
import ReasoningConsole from './components/ReasoningConsole';
import PhaseStream from './components/PhaseStream';
import ErrorBoundary from './components/ErrorBoundary';

function App() {
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [analysisDepth, setAnalysisDepth] = useState('standard');
    const [sessionId, setSessionId] = useState('');
    const [turnCount, setTurnCount] = useState(0);

    const abortRef = useRef(null);

    useEffect(() => {
        setSessionId(getSessionId());
    }, []);

    const handleSend = (query) => {
        setIsLoading(true);
        setTurnCount(prev => prev + 1);

        // Add user query
        setMessages(prev => [...prev, { role: 'user', content: query }]);

        // Add assistant placeholder with initial phase data
        const assistantId = Date.now();
        setMessages(prev => [...prev, {
            id: assistantId,
            role: 'assistant',
            content: '',
            phases: [],
            isStreaming: true
        }]);

        abortRef.current = streamNutriChat(
            query,
            { verbosity: analysisDepth, explanations: true, streaming: true },
            // onPhase
            (phase) => {
                setMessages(prev => prev.map(m =>
                    m.id === assistantId
                        ? { ...m, phases: [...(m.phases || []), phase] }
                        : m
                ));
            },
            // onComplete
            (output) => {
                const finalContent = `### ${output.recipe?.slice(0, 100) || 'Optimized Recipe'}\n\n${output.explanation}`;
                setMessages(prev => prev.map(m =>
                    m.id === assistantId
                        ? { ...m, content: finalContent, isStreaming: false }
                        : m
                ));
                setIsLoading(false);
            },
            // onError
            (err) => {
                console.error(err);
                setIsLoading(false);
                setMessages(prev => prev.filter(m => m.id !== assistantId));
            }
        );
    };

    const handleNewSession = () => {
        clearSession();
        setSessionId(getSessionId());
        setMessages([]);
        setTurnCount(0);
    };

    return (
        <ErrorBoundary>
            <div className="flex h-screen w-screen bg-neutral-950 text-neutral-100 font-sans overflow-hidden selection:bg-accent/30">
                {/* Control Rail - Left */}
                <ControlRail
                    selectedDepth={analysisDepth}
                    onDepthChange={setAnalysisDepth}
                />

                {/* Main Content Area */}
                <div className="flex-1 flex flex-col h-full bg-neutral-900/20">
                    {/* System Telemetry - Top */}
                    <SystemStatus
                        sessionId={sessionId}
                        turnCount={turnCount}
                    />

                    {/* Reasoning Stream - Scrollable */}
                    <PhaseStream messages={messages} />

                    {/* Reasoning Console - Bottom */}
                    <ReasoningConsole
                        onSend={handleSend}
                        isLoading={isLoading}
                        isMemoryActive={turnCount > 0}
                    />
                </div>

                {/* New Session Action - Absolute subtle */}
                <button
                    onClick={handleNewSession}
                    className="absolute top-3 right-4 transform transition-opacity opacity-20 hover:opacity-100 text-[10px] font-mono uppercase tracking-widest border border-neutral-800 px-2 py-0.5 rounded hover:bg-neutral-800"
                >
                    Clear History
                </button>
            </div>
        </ErrorBoundary>
    );
}

export default App;
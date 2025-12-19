import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Loader2, ChefHat, Sparkles, Database, Search, FlaskConical, ChevronDown, ChevronRight, BrainCircuit } from 'lucide-react';
import { getWebSocketURL } from '../config';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import StarBorderButton from './StarBorderButton';

const SOCKET_URL = getWebSocketURL();

const ReasoningAccordion = ({ steps }) => {
    const [isOpen, setIsOpen] = useState(false);

    if (!steps || steps.length === 0) return null;

    return (
        <div className="mb-4 text-left">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 text-xs font-semibold text-kitchen-coffee/60 dark:text-kitchen-text-dark/60 hover:text-kitchen-coffee dark:hover:text-kitchen-text-dark transition-colors bg-black/5 dark:bg-white/5 px-3 py-1.5 rounded-lg"
            >
                {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                <BrainCircuit className="w-4 h-4" />
                <span>Values/Reasoning Process ({steps.length} steps)</span>
            </button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden"
                    >
                        <div className="mt-2 pl-2 border-l-2 border-kitchen-coffee/10 dark:border-kitchen-border-dark space-y-3">
                            {steps.map((step, idx) => (
                                <div key={idx} className="text-sm">
                                    <div className="flex items-center gap-2 mb-1">
                                        {step.stage === 'chemistry' && <FlaskConical className="w-3 h-3 text-blue-500" />}
                                        {step.stage === 'nutrition' && <Database className="w-3 h-3 text-green-500" />}
                                        {step.stage === 'rag' && <Search className="w-3 h-3 text-orange-500" />}
                                        <span className="text-xs font-bold uppercase opacity-50">
                                            {step.stage || 'Thinking'}
                                        </span>
                                    </div>
                                    <div className="text-kitchen-coffee/80 dark:text-kitchen-text-dark/80 bg-white/50 dark:bg-black/20 p-2 rounded text-xs font-mono">
                                        {step.text}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

// Simple thinking pulses for transient status (optional, if you want only the collapsible history)
const ThinkingStatus = ({ text, stage }) => (
    <div className="flex items-center gap-2 text-xs text-kitchen-coffee/50 dark:text-kitchen-text-dark/50 animate-pulse mb-2">
        <Loader2 className="w-3 h-3 animate-spin" />
        <span>{text}</span>
    </div>
);

export default function Chat({ mode }) {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    // We now track reasoning history per message session
    const [currentReasoning, setCurrentReasoning] = useState([]);
    const [transientThinking, setTransientThinking] = useState(null);

    const messagesEndRef = useRef(null);
    const wsRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, currentReasoning, transientThinking]);

    // Initialize WebSocket
    useEffect(() => {
        const connectWs = () => {
            wsRef.current = new WebSocket(SOCKET_URL);

            wsRef.current.onopen = () => {
                console.log("✅ WebSocket Connected");
            };

            wsRef.current.onmessage = (event) => {
                const data = JSON.parse(event.data);

                switch (data.type) {
                    case 'thinking':
                        // Add to reasoning history
                        const step = {
                            text: data.content || data.message,
                            stage: data.stage || 'reasoning'
                        };
                        setCurrentReasoning(prev => [...prev, step]);
                        setTransientThinking(step);
                        break;

                    case 'thinking_chunk':
                        // Stream text into the LAST reasoning step
                        setCurrentReasoning(prev => {
                            if (prev.length === 0) return prev;
                            const lastIdx = prev.length - 1;
                            const newSteps = [...prev];
                            newSteps[lastIdx] = {
                                ...newSteps[lastIdx],
                                text: newSteps[lastIdx].text + data.chunk
                            };
                            return newSteps;
                        });
                        break;

                    case 'response_chunk':
                        setTransientThinking(null); // Stop pulse when typing starts
                        setMessages(prev => {
                            const lastMsg = prev[prev.length - 1];
                            const isNew = !lastMsg || lastMsg.role === 'user' || lastMsg.isComplete;

                            if (isNew) {
                                return [...prev, {
                                    role: 'assistant',
                                    content: data.chunk,
                                    mode: mode,
                                    reasoning: currentReasoning, // Attach reasoning so far
                                    isStreaming: true
                                }];
                            }

                            // Update existing
                            return [
                                ...prev.slice(0, -1),
                                {
                                    ...lastMsg,
                                    content: lastMsg.content + data.chunk,
                                    reasoning: currentReasoning // Keep updating reasoning
                                }
                            ];
                        });
                        break;

                    case 'complete':
                        setIsLoading(false);
                        setTransientThinking(null);
                        setMessages(prev => {
                            const lastMsg = prev[prev.length - 1];
                            if (lastMsg && lastMsg.role === 'assistant') {
                                return [
                                    ...prev.slice(0, -1),
                                    { ...lastMsg, isStreaming: false, isComplete: true, reasoning: currentReasoning }
                                ];
                            }
                            return prev;
                        });
                        // Clear reasoning for next turn
                        // Note: We don't clear right here because the message needs it. 
                        // It's cleared on next sendMessage.
                        break;

                    case 'error':
                        setMessages(prev => [...prev, {
                            role: 'assistant',
                            content: '❌ ' + (data.content || data.message),
                            error: true
                        }]);
                        setIsLoading(false);
                        setTransientThinking(null);
                        break;
                }
            };

            wsRef.current.onclose = () => {
                console.log("⚠️ WebSocket Disconnected, reconnecting...");
                setTimeout(connectWs, 3000);
            };

            wsRef.current.onerror = (err) => {
                console.error("WebSocket Error:", err);
            };
        };

        connectWs();
        return () => wsRef.current?.close();
    }, [mode, currentReasoning]); // dependency on currentReasoning important for closure

    const sendMessage = async () => {
        if (!input.trim() || isLoading) return;

        const userMessage = { role: 'user', content: input };
        setMessages(prev => [...prev, userMessage]);
        const msg = input;
        setInput('');
        setIsLoading(true);
        setCurrentReasoning([]); // Clear previous reasoning
        setTransientThinking({ text: 'Starting analysis...', stage: 'start' });

        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                message: msg,
                mode: mode
            }));
        } else {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: '⚠️ Connection lost. Please wait or refresh.',
                error: true
            }]);
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <div className="flex flex-col h-full">
            {/* Chat messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
                <AnimatePresence>
                    {messages.length === 0 && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="text-center py-12"
                        >
                            <motion.div
                                animate={{
                                    rotate: [0, -10, 10, -10, 0],
                                    transition: { repeat: Infinity, duration: 2 }
                                }}
                                className="text-6xl mb-4 inline-block"
                            >
                                👨‍🍳
                            </motion.div>
                            <h2 className="handwritten text-4xl text-kitchen-coffee dark:text-kitchen-text-dark mb-4">
                                Let's Cook Something Amazing!
                            </h2>
                            <p className="text-kitchen-coffee/70 dark:text-kitchen-text-dark/70 mb-6">
                                Ask me anything about food, nutrition, or recipes
                            </p>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto">
                                {[
                                    { emoji: '🍪', text: 'Make me cookies' },
                                    { emoji: '🥗', text: 'High protein salad' },
                                    { emoji: '🧪', text: 'Why does bread rise?' }
                                ].map((example, i) => (
                                    <motion.button
                                        key={i}
                                        onClick={() => setInput(example.text)}
                                        className="recipe-card p-4 hover:scale-105 transition-transform cursor-pointer"
                                        whileHover={{ y: -4 }}
                                    >
                                        <div className="text-3xl mb-2">{example.emoji}</div>
                                        <div className="text-sm font-medium text-kitchen-coffee dark:text-kitchen-text-dark">
                                            {example.text}
                                        </div>
                                    </motion.button>
                                ))}
                            </div>
                        </motion.div>
                    )}

                    {messages.map((message, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-[85%] ${message.role === 'user'
                                    ? 'message-user'
                                    : 'message-assistant'
                                    }`}
                            >
                                {message.role === 'assistant' && (
                                    <div className="flex items-center gap-2 mb-2 text-kitchen-cinnamon border-b border-kitchen-cinnamon/10 pb-2">
                                        <ChefHat className="w-4 h-4" />
                                        <span className="text-xs font-bold uppercase tracking-wide">
                                            Chef AI • {message.mode || mode} mode
                                        </span>
                                    </div>
                                )}

                                {/* Collapsible Reasoning Section */}
                                {message.role === 'assistant' && message.reasoning && (
                                    <ReasoningAccordion steps={message.reasoning} />
                                )}

                                {/* Main Content with Markdown */}
                                <div className="prose prose-sm max-w-none dark:prose-invert">
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={{
                                            // Fix for spacing issues in lists if needed, mostly handled by standard MD
                                        }}
                                    >
                                        {message.content}
                                    </ReactMarkdown>
                                </div>
                            </div>
                        </motion.div>
                    ))}

                    {/* Active Thinking Status (Transient Pulse) */}
                    {isLoading && transientThinking && (
                        <div className="flex justify-start w-full px-4">
                            <ThinkingStatus text={transientThinking.text} stage={transientThinking.stage} />
                        </div>
                    )}

                </AnimatePresence>

                <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            <div className="border-t-4 border-kitchen-butter dark:border-kitchen-border-dark bg-white dark:bg-kitchen-card-dark p-4">
                <div className="max-w-4xl mx-auto">
                    <div className="flex gap-3">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="Ask me anything about food..."
                            className="kitchen-input flex-1"
                            disabled={isLoading}
                        />
                        <StarBorderButton
                            onClick={sendMessage}
                            disabled={!input.trim() || isLoading}
                            className=""
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    <span>Cooking...</span>
                                </>
                            ) : (
                                <>
                                    <Send className="w-5 h-5" />
                                    <span>Send</span>
                                </>
                            )}
                        </StarBorderButton>
                    </div>
                </div>
            </div>
        </div>
    );
}

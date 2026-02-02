import React from 'react';
import { Sparkles, ChefHat, Microscope } from 'lucide-react';

const STARTER_PROMPTS = [
    {
        text: "Why is my carbonara grainy?",
        icon: ChefHat,
        category: "Diagnostic"
    },
    {
        text: "How to make crispy fried chicken",
        icon: Sparkles,
        category: "Procedural"
    },
    {
        text: "What makes bread fluffy?",
        icon: Microscope,
        category: "Scientific"
    }
];

const StarterPrompts = ({ onSelectPrompt }) => {
    return (
        <div className="max-w-3xl mx-auto px-4 py-8 animate-fade-in">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4">
                {STARTER_PROMPTS.map((prompt, idx) => {
                    const Icon = prompt.icon;
                    return (
                        <button
                            key={idx}
                            onClick={() => onSelectPrompt(prompt.text)}
                            className="group p-4 bg-neutral-900/50 border border-neutral-800 rounded-lg hover:border-accent/40 hover:bg-neutral-900/80 transition-all duration-200 text-left active:scale-[0.98]"
                        >
                            <div className="flex items-start gap-3">
                                <div className="p-2 bg-neutral-800/50 rounded-md group-hover:bg-accent/10 transition-colors">
                                    <Icon className="w-4 h-4 text-neutral-500 group-hover:text-accent transition-colors" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm text-neutral-300 group-hover:text-neutral-100 transition-colors leading-relaxed">
                                        {prompt.text}
                                    </p>
                                    <span className="text-[10px] text-neutral-600 font-mono uppercase tracking-wider mt-1 block">
                                        {prompt.category}
                                    </span>
                                </div>
                            </div>
                        </button>
                    );
                })}
            </div>
        </div>
    );
};

export default StarterPrompts;

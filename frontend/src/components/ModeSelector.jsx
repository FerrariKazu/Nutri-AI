/**
 * DUMB COMPONENT - Just renders mode cards
 * Calls API function to change mode, updates UI state
 */

import React, { useState } from 'react';
import { setMode } from '../api/apiClient';
import ModeCardWithAnimation from './ModeCardWithAnimation';

const ModeSelector = ({ currentMode, onModeChange, selectedMode, onSelect }) => {
    // Support both props for backward compatibility
    const mode = currentMode || selectedMode;
    const onChange = onModeChange || onSelect;

    const [isChanging, setIsChanging] = useState(false);

    const modes = [
        {
            id: 'simple',
            icon: '🍳',
            title: 'Simple',
            description: 'Just the recipe - quick & easy',
            bgColor: 'bg-green-100/90',
        },
        {
            id: 'standard',
            icon: '🧑‍🍳',
            title: 'Standard',
            description: 'Recipe + interesting science',
            bgColor: 'bg-yellow-100/90',
        },
        {
            id: 'chemistry',
            icon: '🧪',
            title: 'Chemistry',
            description: 'Full molecular detail',
            bgColor: 'bg-blue-100/90',
        },
    ];

    /**
     * Handle mode change - just call API function
     */
    const handleModeChange = async (modeId) => {
        if (modeId === mode || isChanging) return;

        setIsChanging(true);

        // Call API function
        const success = await setMode(modeId);

        if (success) {
            onChange(modeId);
        } else {
            // Show error (could use toast notification)
            console.error('Failed to change mode');
        }

        setIsChanging(false);
    };

    return (
        <div className="p-4 space-y-4">
            {modes.map(m => (
                <ModeCardWithAnimation
                    key={m.id}
                    mode={m.id}
                    icon={m.icon}
                    title={m.title}
                    description={m.description}
                    bgColor={m.id === mode ? m.bgColor : 'bg-white/30 dark:bg-white/10'}
                    isSelected={m.id === mode}
                    onClick={() => handleModeChange(m.id)}
                />
            ))}

            {isChanging && (
                <div className="text-center text-sm text-gray-500 dark:text-gray-400">
                    Switching mode...
                </div>
            )}
        </div>
    );
};

export default ModeSelector;
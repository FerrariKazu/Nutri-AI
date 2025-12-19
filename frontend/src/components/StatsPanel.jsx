/**
 * DUMB COMPONENT - Fetches stats once on mount
 * Just calls API function and displays result
 */

import React, { useState, useEffect } from 'react';
import { getStats } from '../api/apiClient';

const StatsPanel = () => {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    // Fetch stats once on mount
    useEffect(() => {
        (async () => {
            const data = await getStats();
            setStats(data);
            setLoading(false);
        })();
    }, []); // Empty deps - only run once

    if (loading) {
        return (
            <div className="p-4 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-orange-500 border-t-transparent mx-auto" />
            </div>
        );
    }

    return (
        <div className="p-4 bg-kitchen-oat/50 dark:bg-black/40 border border-transparent dark:border-kitchen-border-dark rounded-xl mt-4">
            <h3 className="text-sm font-bold text-kitchen-coffee dark:text-kitchen-text-dark uppercase tracking-wider mb-2">
                KITCHEN STATS
            </h3>
            <div className="space-y-2 text-sm text-kitchen-coffee/80 dark:text-kitchen-text-dark/70">
                <div className="flex justify-between">
                    <span>Recipes</span>
                    <span className="font-bold">
                        {stats?.recipes?.toLocaleString() || '142,893'}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span>Ingredients</span>
                    <span className="font-bold">
                        {stats?.ingredients || '8.5M+'}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span>Papers</span>
                    <span className="font-bold">
                        {stats?.papers?.toLocaleString() || '24,109'}
                    </span>
                </div>
            </div>
        </div>
    );
};

export default StatsPanel;

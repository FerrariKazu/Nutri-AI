/**
 * Animated Mode Selection Card
 * Adds shimmer effect on hover
 */

import React from 'react';
import { motion } from 'framer-motion';

const ModeCardWithAnimation = ({
    mode,
    icon,
    title,
    description,
    isSelected,
    onClick,
    bgColor = 'bg-white'
}) => {
    return (
        <motion.div
            onClick={onClick}
            className={`
        relative rounded-xl p-3 sm:p-4 cursor-pointer
        border-2 transition-all duration-300 backdrop-blur-md
        ${bgColor}
        ${isSelected
                    ? 'border-orange-400/60 shadow-lg scale-[1.02] sm:scale-105'
                    : 'border-white/30 dark:border-white/20 hover:border-orange-300/50 hover:shadow-md'
                }
      `}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.98 }}
        >
            {/* Shimmer effect on hover */}
            {!isSelected && (
                <motion.div
                    className="absolute inset-0 rounded-xl opacity-0 hover:opacity-100 pointer-events-none"
                    initial={{ background: 'linear-gradient(90deg, transparent, rgba(251, 146, 60, 0.15), transparent)' }}
                    animate={{
                        backgroundPosition: ['200% 0', '-200% 0'],
                    }}
                    transition={{
                        duration: 1.5,
                        repeat: Infinity,
                        ease: 'linear'
                    }}
                    style={{
                        backgroundSize: '200% 100%'
                    }}
                />
            )}

            {/* Content */}
            <div className="relative flex items-center gap-2 sm:gap-3">
                <span className="text-xl sm:text-2xl md:text-3xl flex-shrink-0">{icon}</span>
                <div className="flex-1 min-w-0">
                    <h3 className={`font-bold text-sm sm:text-base truncate ${isSelected ? 'text-orange-900 dark:text-orange-300' : 'text-gray-800 dark:text-gray-200'}`}>
                        {title}
                    </h3>
                    <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-1">{description}</p>
                </div>

                {/* Check mark for selected */}
                {isSelected && (
                    <motion.div
                        className="bg-orange-500 text-white rounded-full p-1 flex-shrink-0"
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: 'spring', stiffness: 500, damping: 15 }}
                    >
                        <svg className="w-3 h-3 sm:w-4 sm:h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" />
                        </svg>
                    </motion.div>
                )}
            </div>

            {/* Glow effect when selected */}
            {isSelected && (
                <motion.div
                    className="absolute inset-0 rounded-xl bg-gradient-to-r from-orange-400/15 to-red-400/15 blur-xl pointer-events-none"
                    animate={{
                        opacity: [0.3, 0.6, 0.3],
                    }}
                    transition={{
                        duration: 2,
                        repeat: Infinity,
                        ease: 'easeInOut'
                    }}
                    style={{ zIndex: -1 }}
                />
            )}
        </motion.div>
    );
};

export default ModeCardWithAnimation;
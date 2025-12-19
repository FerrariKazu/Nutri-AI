/**
 * Star Border Button with animated border effect
 * Based on: https://reactbits.dev/animations/star-border
 * 
 * Features:
 * - Animated rotating gradient border
 * - Particle sparkle effect on hover
 * - Smooth transitions
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';

const StarBorderButton = ({
    onClick,
    disabled = false,
    children,
    className = ''
}) => {
    const [isHovered, setIsHovered] = useState(false);

    return (
        <motion.div
            className={`relative ${className}`}
            onHoverStart={() => setIsHovered(true)}
            onHoverEnd={() => setIsHovered(false)}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
        >
            {/* Animated Border Container */}
            <div className="relative group">
                {/* Rotating Gradient Border */}
                <div
                    className={`
            absolute inset-0 rounded-xl
            bg-gradient-to-r from-orange-400 via-red-500 to-pink-500
            opacity-75 group-hover:opacity-100
            blur-sm group-hover:blur-md
            transition-all duration-300
            ${disabled ? 'opacity-30' : ''}
            ${isHovered && !disabled ? 'animate-spin-slow' : ''}
          `}
                />

                {/* Inner Button */}
                <button
                    onClick={onClick}
                    disabled={disabled}
                    className={`
            relative px-6 py-3 rounded-xl
            bg-gradient-to-br from-orange-400 to-orange-500
            text-white font-semibold
            shadow-lg hover:shadow-xl
            transition-all duration-300
            disabled:opacity-50 disabled:cursor-not-allowed
            flex items-center gap-2
            w-full justify-center
            ${disabled ? '' : 'hover:from-orange-500 hover:to-orange-600'}
          `}
                >
                    {/* Sparkle particles on hover */}
                    {isHovered && !disabled && (
                        <>
                            <SparkleParticle delay={0} />
                            <SparkleParticle delay={0.1} />
                            <SparkleParticle delay={0.2} />
                            <SparkleParticle delay={0.3} />
                        </>
                    )}

                    {children}
                </button>
            </div>
        </motion.div>
    );
};

// Sparkle particle component
const SparkleParticle = ({ delay }) => {
    const randomX = Math.random() * 40 - 20;
    const randomY = Math.random() * 40 - 20;

    return (
        <motion.div
            className="absolute w-1 h-1 bg-white rounded-full"
            initial={{
                opacity: 0,
                scale: 0,
                x: 0,
                y: 0
            }}
            animate={{
                opacity: [0, 1, 0],
                scale: [0, 1.5, 0],
                x: randomX,
                y: randomY
            }}
            transition={{
                duration: 0.8,
                delay: delay,
                repeat: Infinity,
                repeatDelay: 0.5
            }}
        />
    );
};

export default StarBorderButton;

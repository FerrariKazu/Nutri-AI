/**
 * Floating Lines Background
 * Animated background with floating line particles
 * Based on: https://reactbits.dev/backgrounds/floating-lines
 */

import React, { useEffect, useRef } from 'react';
import { animationConfig } from '../utils/performanceOptimizer';

const FloatingLinesBackground = ({
    lineColor = 'rgba(251, 146, 60, 0.3)', // Orange to match your theme
    lineCount = 30,
    speed = 0.5,
    className = ''
}) => {
    const canvasRef = useRef(null);
    const linesRef = useRef([]);
    const animationFrameRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        // Set canvas size
        const resizeCanvas = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        };
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);

        // Initialize lines
        class Line {
            constructor() {
                this.reset();
            }

            reset() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.length = Math.random() * 100 + 50;
                this.angle = Math.random() * Math.PI * 2;
                this.speed = Math.random() * speed + 0.2;
                this.opacity = Math.random() * 0.5 + 0.2;
            }

            update() {
                this.x += Math.cos(this.angle) * this.speed;
                this.y += Math.sin(this.angle) * this.speed;

                // Wrap around edges
                if (this.x < -this.length) this.x = canvas.width + this.length;
                if (this.x > canvas.width + this.length) this.x = -this.length;
                if (this.y < -this.length) this.y = canvas.height + this.length;
                if (this.y > canvas.height + this.length) this.y = -this.length;
            }

            draw() {
                ctx.save();
                ctx.translate(this.x, this.y);
                ctx.rotate(this.angle);

                ctx.strokeStyle = lineColor.replace('0.3', this.opacity.toString());
                ctx.lineWidth = 2;
                ctx.lineCap = 'round';

                ctx.beginPath();
                ctx.moveTo(0, 0);
                ctx.lineTo(this.length, 0);
                ctx.stroke();

                ctx.restore();
            }
        }

        // Create lines
        const optimalLineCount = animationConfig ? animationConfig.getOptimalParticleCount() : lineCount;
        linesRef.current = Array.from({ length: optimalLineCount }, () => new Line());

        // Animation loop
        const animate = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            linesRef.current.forEach(line => {
                line.update();
                line.draw();
            });

            animationFrameRef.current = requestAnimationFrame(animate);
        };

        if (!animationConfig || animationConfig.shouldAnimate) {
            animate();
        }

        // Cleanup
        return () => {
            window.removeEventListener('resize', resizeCanvas);
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current);
            }
        };
    }, [lineColor, lineCount, speed]);

    return (
        <canvas
            ref={canvasRef}
            className={`fixed inset-0 pointer-events-none ${className}`}
            style={{
                zIndex: 0,
                // Using CSS variable for theme awareness or default
                // Since we are in App.jsx which uses kitchen-cream, we can set transparent 
                // effectively letting the parent background show through, OR enforce the gradient.
                // User asked for 'Cream/beige base' but App.jsx uses specific tailwind colors.
                // Let's make it transparent so it overlays the App's existing background.
                background: 'transparent'
            }}
        />
    );
};

export default FloatingLinesBackground;

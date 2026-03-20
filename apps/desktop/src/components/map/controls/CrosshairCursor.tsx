import { useState, useEffect } from 'react';
import { motion, useMotionValue, useSpring } from 'framer-motion';
import { clsx } from 'clsx';
import { useMapStore } from '@/stores/useMapStore';

export function CrosshairCursor() {
    const { viewState } = useMapStore();
    const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
    const [isHoveringEntity, setIsHoveringEntity] = useState(false);

    const cursorX = useSpring(useMotionValue(0), { damping: 25, stiffness: 200 });
    const cursorY = useSpring(useMotionValue(0), { damping: 25, stiffness: 200 });

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            setMousePos({ x: e.clientX, y: e.clientY });
            cursorX.set(e.clientX);
            cursorY.set(e.clientY);

            // Check if hovering over an entity (this assumes entities have a specific class or we can detect it,
            // for now we'll simulate it based on cursor style or elements under cursor if needed)
            const element = document.elementFromPoint(e.clientX, e.clientY);
            const isEntity = element?.tagName.toLowerCase() === 'circle' || element?.closest('.deck-tooltip');
            setIsHoveringEntity(!!isEntity);
        };

        window.addEventListener('mousemove', handleMouseMove);
        return () => window.removeEventListener('mousemove', handleMouseMove);
    }, [cursorX, cursorY]);

    // Approximate coordinate calculation based on screen pos and viewState (simplified for visual effect)
    // In a real Deck.gl app, we'd use deck.gl's getMapPosition or project/unproject
    const approxLng = (viewState.longitude + (mousePos.x - window.innerWidth / 2) * (viewState.zoom * 0.005)).toFixed(4);
    const approxLat = (viewState.latitude - (mousePos.y - window.innerHeight / 2) * (viewState.zoom * 0.005)).toFixed(4);

    return (
        <>
            <motion.div
                className={clsx(
                    "fixed top-0 left-0 w-8 h-8 pointer-events-none z-[100] mix-blend-screen transition-colors duration-300",
                    isHoveringEntity ? "text-nexus-red" : "text-nexus-cyan"
                )}
                style={{
                    x: cursorX,
                    y: cursorY,
                    translateX: '-50%',
                    translateY: '-50%',
                }}
            >
                <svg viewBox="0 0 100 100" className="w-full h-full drop-shadow-[0_0_8px_currentColor]">
                    {/* Crosshair Lines */}
                    <line x1="50" y1="0" x2="50" y2="35" stroke="currentColor" strokeWidth="2" />
                    <line x1="50" y1="65" x2="50" y2="100" stroke="currentColor" strokeWidth="2" />
                    <line x1="0" y1="50" x2="35" y2="50" stroke="currentColor" strokeWidth="2" />
                    <line x1="65" y1="50" x2="100" y2="50" stroke="currentColor" strokeWidth="2" />

                    {/* Center Dot */}
                    <circle cx="50" cy="50" r="4" fill="currentColor" />

                    {/* Animated Target Ring */}
                    {isHoveringEntity && (
                        <motion.circle
                            cx="50" cy="50" r="45"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1"
                            strokeDasharray="10 10"
                            animate={{ rotate: 360 }}
                            transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                        />
                    )}
                </svg>

                {/* Coordinates Tooltip */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="absolute top-full left-full mt-2 ml-2 bg-nexus-bg-glass backdrop-blur-md border border-nexus-border/50 rounded px-2 py-1 flex flex-col gap-0.5 whitespace-nowrap"
                >
                    <span className="text-[9px] font-mono text-nexus-text">LAT: {approxLat}°</span>
                    <span className="text-[9px] font-mono text-nexus-text">LNG: {approxLng}°</span>
                    {isHoveringEntity && (
                        <span className="text-[9px] font-mono text-nexus-red animate-pulse mt-0.5">TARGET LOCKED</span>
                    )}
                </motion.div>
            </motion.div>

            {/* Hide default cursor globally while in map view (handled in CSS usually, but adding a dev-friendly style here) */}
            <style>{`
        .deck-gl-canvas { cursor: none !important; }
      `}</style>
        </>
    );
}

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { SOS_BUTTON_ARIA } from '../../../lib/strings';

interface SosButtonProps {
  onTriggered: () => void;
}

const HOLD_DURATION_MS = 1500;
const RING_RADIUS = 72;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

/**
 * 1.5-second continuous press-and-hold SOS emergency trigger.
 *
 * Stress-proof design constraints:
 * - Must hold continuously for 1500ms — accidental taps do NOT trigger
 * - SVG progress ring provides clear visual feedback of hold progress
 * - Haptic feedback: short tick on start, multi-pulse on trigger
 * - Keyboard accessible: Space/Enter keys work like mouse/touch press-and-hold
 */
export function SosButton({ onTriggered }: SosButtonProps) {
  const [progress, setProgress] = useState(0); // 0–1
  const [isHolding, setIsHolding] = useState(false);
  const holdStart = useRef<number | null>(null);
  const rafId = useRef<number | null>(null);
  const triggered = useRef(false);

  const cancelHold = useCallback(() => {
    setIsHolding(false);
    setProgress(0);
    holdStart.current = null;
    triggered.current = false;
    if (rafId.current !== null) {
      cancelAnimationFrame(rafId.current);
      rafId.current = null;
    }
  }, []);

  const startHold = useCallback(() => {
    if (triggered.current) return;
    setIsHolding(true);
    holdStart.current = performance.now();

    // Haptic tick on start
    try { navigator.vibrate?.(20); } catch { /* ignore */ }

    const tick = () => {
      if (holdStart.current === null) return;
      const elapsed = performance.now() - holdStart.current;
      const p = Math.min(elapsed / HOLD_DURATION_MS, 1);
      setProgress(p);

      if (p >= 1 && !triggered.current) {
        triggered.current = true;
        setIsHolding(false);
        setProgress(0);
        // Multi-pulse haptic on completion
        try { navigator.vibrate?.([40, 60, 40]); } catch { /* ignore */ }
        onTriggered();
        return;
      }

      rafId.current = requestAnimationFrame(tick);
    };

    rafId.current = requestAnimationFrame(tick);
  }, [onTriggered]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (rafId.current !== null) cancelAnimationFrame(rafId.current);
    };
  }, []);

  const dashOffset = RING_CIRCUMFERENCE * (1 - progress);

  return (
    <button
      id="sos-button"
      type="button"
      aria-label={SOS_BUTTON_ARIA}
      className="relative w-44 h-44 rounded-full focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-red-600 focus-visible:ring-offset-4 select-none"
      onMouseDown={startHold}
      onMouseUp={cancelHold}
      onMouseLeave={cancelHold}
      onTouchStart={(e) => { e.preventDefault(); startHold(); }}
      onTouchEnd={cancelHold}
      onTouchCancel={cancelHold}
      onKeyDown={(e) => { if ((e.key === ' ' || e.key === 'Enter') && !e.repeat) startHold(); }}
      onKeyUp={(e) => { if (e.key === ' ' || e.key === 'Enter') cancelHold(); }}
    >
      {/* SVG progress ring */}
      <svg
        className="absolute inset-0 w-full h-full -rotate-90"
        viewBox="0 0 160 160"
        aria-hidden="true"
      >
        {/* Track */}
        <circle
          cx="80" cy="80" r={RING_RADIUS}
          fill="none"
          stroke="rgba(239,68,68,0.15)"
          strokeWidth="6"
        />
        {/* Progress arc */}
        <circle
          cx="80" cy="80" r={RING_RADIUS}
          fill="none"
          stroke="#dc2626"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={RING_CIRCUMFERENCE}
          strokeDashoffset={dashOffset}
          style={{ transition: isHolding ? 'none' : 'stroke-dashoffset 0.1s ease' }}
        />
      </svg>

      {/* Inner circle */}
      <div
        className={`
          absolute inset-3 rounded-full bg-red-600 shadow-2xl
          flex flex-col items-center justify-center
          transition-transform duration-75
          ${isHolding ? 'scale-95' : 'scale-100'}
          ${isHolding ? 'shadow-red-500/60' : ''}
        `}
      >
        <span className="text-white font-black text-xl tracking-wider leading-none">SOS</span>
        <span className="text-red-100 text-[10px] font-semibold mt-1 leading-none">
          {isHolding ? 'Hold...' : 'HOLD 1.5s'}
        </span>
      </div>
    </button>
  );
}

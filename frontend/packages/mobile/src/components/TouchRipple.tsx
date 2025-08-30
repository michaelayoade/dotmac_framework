import React, { useEffect, useState } from 'react';
import { clsx } from 'clsx';

interface TouchRippleProps {
  show: boolean;
  x: number;
  y: number;
  color?: string;
  duration?: number;
  size?: number;
}

export function TouchRipple({
  show,
  x,
  y,
  color = 'rgba(255, 255, 255, 0.6)',
  duration = 300,
  size = 100
}: TouchRippleProps) {
  const [animate, setAnimate] = useState(false);

  useEffect(() => {
    if (show) {
      setAnimate(true);

      const timer = setTimeout(() => {
        setAnimate(false);
      }, duration);

      return () => clearTimeout(timer);
    } else {
      setAnimate(false);
    }
  }, [show, duration]);

  if (!show && !animate) return null;

  return (
    <span
      className={clsx(
        'absolute rounded-full pointer-events-none transform -translate-x-1/2 -translate-y-1/2',
        'animate-ripple'
      )}
      style={{
        left: x,
        top: y,
        width: size,
        height: size,
        backgroundColor: color,
        animationDuration: `${duration}ms`
      }}
    />
  );
}

// CSS animation for ripple effect
TouchRipple.styles = `
  @keyframes ripple {
    0% {
      transform: translate(-50%, -50%) scale(0);
      opacity: 1;
    }
    100% {
      transform: translate(-50%, -50%) scale(1);
      opacity: 0;
    }
  }

  .animate-ripple {
    animation: ripple 300ms ease-out;
  }
`;

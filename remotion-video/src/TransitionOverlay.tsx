import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';

export const TransitionOverlay: React.FC<{
  type: 'in' | 'out';
  duration: number;
}> = ({ type, duration }) => {
  const frame = useCurrentFrame();

  const opacity =
    type === 'in'
      ? interpolate(frame, [0, duration], [1, 0])
      : interpolate(frame, [0, duration], [0, 1]);

  const blur =
    type === 'in'
      ? interpolate(frame, [0, duration], [15, 0])
      : interpolate(frame, [0, duration], [0, 15]);

  return (
    <div
      className="absolute inset-0 z-50 pointer-events-none"
      style={{
        // Deep blood-red fade instead of plain black
        backgroundColor: `rgba(40, 0, 0, ${opacity})`,
        backdropFilter: `blur(${blur}px)`,
        boxShadow: opacity > 0.05
          ? `inset 0 0 80px rgba(180, 0, 0, ${opacity * 0.6})`
          : 'none',
      }}
    />
  );
};

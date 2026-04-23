import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';

export const TransitionOverlay: React.FC<{
  type: 'in' | 'out';
  duration: number;
}> = ({ type, duration }) => {
  const frame = useCurrentFrame();

  const opacity = type === 'in' 
    ? interpolate(frame, [0, duration], [1, 0])
    : interpolate(frame, [0, duration], [0, 1]);

  const blur = type === 'in'
    ? interpolate(frame, [0, duration], [20, 0])
    : interpolate(frame, [0, duration], [0, 20]);

  return (
    <div
      className="absolute inset-0 z-50 bg-black pointer-events-none"
      style={{
        opacity,
        backdropFilter: `blur(${blur}px)`,
      }}
    />
  );
};

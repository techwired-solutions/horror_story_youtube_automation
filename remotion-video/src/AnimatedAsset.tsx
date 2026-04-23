import React from 'react';
import { interpolate, useCurrentFrame, spring, useVideoConfig } from 'remotion';

export const AnimatedAsset: React.FC<{
  src: string;
  durationInFrames: number;
  animationType: 'zoom' | 'pop' | 'slide_up' | 'slide_down' | 'fade';
}> = ({ src, durationInFrames, animationType }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 1. Zoom (Ken Burns)
  const scaleZoom = interpolate(
    frame,
    [0, durationInFrames],
    [1, 1.25],
    { extrapolateRight: 'clamp' }
  );

  // 2. Pop (Spring)
  const popSpring = spring({
    frame,
    fps,
    config: {
      stiffness: 100,
      damping: 10,
    },
  });
  const scalePop = interpolate(popSpring, [0, 1], [0.8, 1]);

  // 3. Slide Up/Down
  const translateY = interpolate(
    frame,
    [0, 30], // Smooth entry over 1 second
    [animationType === 'slide_up' ? 100 : -100, 0],
    { extrapolateRight: 'clamp' }
  );

  // 4. Fade
  const opacity = interpolate(
    frame,
    [0, 15, durationInFrames - 15, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateRight: 'clamp' }
  );

  const getStyles = () => {
    switch (animationType) {
      case 'zoom':
        return { transform: `scale(${scaleZoom})` };
      case 'pop':
        return { transform: `scale(${scalePop})` };
      case 'slide_up':
      case 'slide_down':
        return { transform: `translateY(${translateY}px)` };
      case 'fade':
      default:
        return { opacity };
    }
  };

  return (
    <div className="absolute inset-0 overflow-hidden bg-black">
      <div
        className="w-full h-full"
        style={{
          ...getStyles(),
          filter: 'contrast(1.2) brightness(0.7) sepia(0.1)', // Chilling aesthetic
          transition: 'filter 0.5s ease-in-out',
        }}
      >
        <img
          src={src}
          className="w-full h-full object-cover"
          alt="horror scene"
        />
      </div>
      
      {/* Dark vignette overlay for depth */}
      <div className="absolute inset-0 pointer-events-none" 
           style={{ background: 'radial-gradient(circle, transparent 40%, rgba(0,0,0,0.8) 100%)' }} />
    </div>
  );
};

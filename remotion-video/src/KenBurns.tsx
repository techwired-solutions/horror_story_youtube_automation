import React from 'react';
import { interpolate, useCurrentFrame, Video, OffthreadVideo } from 'remotion';

export const KenBurns: React.FC<{
  src: string;
  durationInFrames: number;
  type: 'video' | 'image';
}> = ({ src, durationInFrames, type }) => {
  const frame = useCurrentFrame();

  const scale = interpolate(
    frame,
    [0, durationInFrames],
    [1, 1.2],
    { extrapolateRight: 'clamp' }
  );

  const x = interpolate(
    frame,
    [0, durationInFrames],
    [0, 10],
    { extrapolateRight: 'clamp' }
  );

  return (
    <div className="absolute inset-0 overflow-hidden bg-black">
      <div
        className="w-full h-full"
        style={{
          transform: `scale(${scale}) translateX(${x}px)`,
          filter: 'contrast(1.2) brightness(0.8) grayscale(0.2)' // Chilling aesthetic
        }}
      >
        {type === 'video' ? (
          <OffthreadVideo
            src={src}
            className="w-full h-full object-cover"
          />
        ) : (
          <img
            src={src}
            className="w-full h-full object-cover"
            alt="background"
          />
        )}
      </div>
    </div>
  );
};

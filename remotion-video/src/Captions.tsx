import React from 'react';
import { interpolate, useCurrentFrame, spring } from 'remotion';

export interface Subtitle {
  text: string;
  start: number;
  end: number;
}

export const Captions: React.FC<{
  subtitles: Subtitle[];
  fps: number;
}> = ({ subtitles, fps }) => {
  const frame = useCurrentFrame();

  return (
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none p-10">
      <div className="text-center w-full">
        {subtitles.map((sub, index) => {
          const startFrame = sub.start * fps;
          const endFrame = sub.end * fps;
          const isActive = frame >= startFrame && frame < endFrame;

          if (!isActive) return null;

          const progress = spring({
            frame: frame - startFrame,
            fps,
            config: {
              damping: 10,
              stiffness: 100,
            },
          });

          const scale = interpolate(progress, [0, 1], [1, 1.3]);
          const glow = interpolate(progress, [0, 1], [0, 20]);
          
          return (
            <div
              key={index}
              className="text-7xl font-black uppercase italic tracking-tighter text-white"
              style={{
                transform: `scale(${scale}) rotate(${index % 2 === 0 ? '-2deg' : '2deg'})`,
                color: '#ff4d4d', // Blood red horror color
                textShadow: `0 0 ${glow}px rgba(255, 0, 0, 0.8), 0 5px 15px rgba(0,0,0,0.9)`,
                filter: 'drop-shadow(0 5px 10px rgba(0,0,0,1))'
              }}
            >
              {sub.text}
            </div>
          );
        })}
      </div>
    </div>
  );
};

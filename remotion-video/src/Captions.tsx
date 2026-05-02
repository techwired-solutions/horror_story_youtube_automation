import React from 'react';
import { useCurrentFrame, spring } from 'remotion';

export interface Subtitle {
  text: string;
  start: number;
  end: number;
}

function isImpactWord(text: string): boolean {
  const clean = text.replace(/[^\w]/g, '');
  if (!clean) return false;
  return clean.length >= 5 || clean === clean.toUpperCase();
}

export const Captions: React.FC<{
  subtitles: Subtitle[];
  fps: number;
}> = ({ subtitles, fps }) => {
  const frame = useCurrentFrame();

  if (!subtitles || subtitles.length === 0) return null;

  // Find the currently active word
  const activeIndex = subtitles.findIndex((word, index) => {
    const startFrame = word.start * fps;
    let endFrame = word.end * fps;
    
    // Gap-based boundary detection: keep word visible until the next word
    if (index < subtitles.length - 1) {
      const nextStartFrame = subtitles[index + 1].start * fps;
      // If the gap to the next word is less than 2 seconds, keep word on screen
      if (nextStartFrame - endFrame < 2 * fps) {
        endFrame = nextStartFrame;
      }
    } else {
      // Keep last word on screen slightly longer
      endFrame += 2 * fps;
    }
    
    return frame >= startFrame && frame < endFrame;
  });

  if (activeIndex === -1) return null;

  const word = subtitles[activeIndex];
  const wordStartFrame = word.start * fps;
  const framesIntoWord = Math.max(0, frame - wordStartFrame);

  const wordSpring = spring({
    frame: framesIntoWord,
    fps,
    config: { stiffness: 250, damping: 16 },
  });

  const impact = isImpactWord(word.text);

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        bottom: 0,
        left: 0,
        right: 0,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        pointerEvents: 'none',
        zIndex: 100,
      }}
    >
      <div
        style={{
          textAlign: 'center',
          width: '90%',
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <span
          style={{
            fontSize: impact ? '140px' : '110px',
            fontFamily: 'Montserrat, Impact, "Arial Black", sans-serif',
            fontWeight: '900',
            lineHeight: '1.05',
            letterSpacing: impact ? '-2px' : '-1px',
            display: 'inline-block',
            transform: `scale(${wordSpring})`,
            color: impact ? '#FF1A1A' : '#FFFFFF',
            textShadow: impact
              ? '0 0 30px rgba(255,26,26,0.8), 4px 4px 12px rgba(0,0,0,0.9)'
              : '4px 4px 16px rgba(0,0,0,0.95)',
            WebkitTextStroke: impact ? '2px rgba(200,0,0,0.8)' : '1px rgba(0,0,0,0.5)',
          }}
        >
          {word.text}
        </span>
      </div>
    </div>
  );
};

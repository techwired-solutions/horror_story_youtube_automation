import React from 'react';
import { useCurrentFrame, spring, interpolate } from 'remotion';

export interface Subtitle {
  text: string;
  start: number;
  end: number;
}

function isImpactWord(text: string): boolean {
  const clean = text.replace(/[^\w]/g, '');
  if (!clean) return false;
  // Impact words: long words or ALL CAPS
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
      // If the gap to the next word is less than 2 seconds, bridge to next word
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

  // Pop-in spring animation
  const wordSpring = spring({
    frame: framesIntoWord,
    fps,
    config: { stiffness: 300, damping: 18 },
  });

  // Subtle vertical float effect
  const floatY = interpolate(wordSpring, [0, 1], [20, 0]);

  const impact = isImpactWord(word.text);

  // Scale font size: short words get boosted so they stay visually prominent
  // 1–2 chars → 148px, 3–4 chars → 128px, 5+ chars (impact) → 136px, others → 108px
  const charLen = word.text.replace(/[^\w]/g, '').length;
  const fontSize = impact
    ? 136
    : charLen <= 2
    ? 148
    : charLen <= 4
    ? 128
    : 108;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        bottom: 0,
        left: 0,
        right: 0,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'flex-end',      // anchor to bottom
        alignItems: 'center',
        paddingBottom: '220px',          // lower-third position above waveform
        pointerEvents: 'none',
        zIndex: 100,
      }}
    >
      <div
        style={{
          display: 'inline-flex',
          justifyContent: 'center',
          alignItems: 'center',
          transform: `scale(${wordSpring}) translateY(${floatY}px)`,
        }}
      >
        {/* Semi-transparent pill behind text for legibility */}
        <div
          style={{
            position: 'relative',
            paddingLeft: '24px',
            paddingRight: '24px',
            paddingTop: '8px',
            paddingBottom: '8px',
            borderRadius: '16px',
            background: impact
              ? 'rgba(120, 0, 0, 0.55)'
              : 'rgba(0, 0, 0, 0.45)',
            backdropFilter: 'blur(4px)',
            boxShadow: impact
              ? '0 0 40px rgba(255,0,0,0.4), 0 4px 24px rgba(0,0,0,0.8)'
              : '0 4px 24px rgba(0,0,0,0.7)',
            border: impact ? '1px solid rgba(255,50,50,0.4)' : '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <span
            style={{
              fontSize: `${fontSize}px`,
              fontFamily: 'Montserrat, Impact, "Arial Black", sans-serif',
              fontWeight: '900',
              lineHeight: '1.0',
              letterSpacing: impact ? '-2px' : charLen <= 2 ? '4px' : '-1px',
              display: 'inline-block',
              color: impact ? '#FF2020' : '#FFFFFF',
              textShadow: impact
                ? '0 0 40px rgba(255,30,30,1), 0 0 80px rgba(255,0,0,0.5), 4px 4px 12px rgba(0,0,0,0.95)'
                : '3px 3px 12px rgba(0,0,0,0.99), 0 0 20px rgba(0,0,0,0.8)',
              WebkitTextStroke: impact ? '2px rgba(180,0,0,0.9)' : '1.5px rgba(0,0,0,0.8)',
            }}
          >
            {word.text}
          </span>
        </div>
      </div>
    </div>
  );
};

import React from 'react';
import { interpolate, useCurrentFrame, spring } from 'remotion';

export interface Subtitle {
  text: string;
  start: number;
  end: number;
}

interface WordChunk {
  words: Subtitle[];
  start: number;
  end: number;
}

function groupIntoChunks(subtitles: Subtitle[], maxWords = 4): WordChunk[] {
  const chunks: WordChunk[] = [];
  for (let i = 0; i < subtitles.length; i += maxWords) {
    const words = subtitles.slice(i, i + maxWords);
    chunks.push({
      words,
      start: words[0].start,
      end: words[words.length - 1].end,
    });
  }
  return chunks;
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

  const chunks = groupIntoChunks(subtitles, 4);

  // Find the currently active chunk (with 1s tail buffer so it doesn't vanish abruptly)
  const activeChunk = chunks.find((chunk) => {
    const startFrame = chunk.start * fps;
    const endFrame = chunk.end * fps + fps; // 1s buffer
    return frame >= startFrame && frame < endFrame;
  });

  if (!activeChunk) return null;

  const chunkStartFrame = activeChunk.start * fps;
  const framesIntoChunk = Math.max(0, frame - chunkStartFrame);

  // Slide-Up Pop — spring on container entry
  const containerSpring = spring({
    frame: framesIntoChunk,
    fps,
    config: { stiffness: 200, damping: 14 },
  });
  const slideY = interpolate(containerSpring, [0, 1], [80, 0]);
  const containerScale = interpolate(containerSpring, [0, 1], [0.85, 1.0]);

  // Camera Shake — subtle sin oscillation on X axis
  const shake = Math.sin(frame * 0.4) * 1.5;

  // Bottom Accent Bar fade-in
  const accentSpring = spring({
    frame: framesIntoChunk,
    fps,
    config: { stiffness: 150, damping: 20 },
  });
  const accentOpacity = interpolate(accentSpring, [0, 1], [0, 1]);

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 130,
        left: 0,
        right: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '0 28px',
        pointerEvents: 'none',
        transform: `translateY(${slideY}px) scale(${containerScale}) translateX(${shake}px)`,
      }}
    >
      {/* Word-by-Word Pop-In */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: '6px 14px',
          textAlign: 'center',
        }}
      >
        {activeChunk.words.map((word, idx) => {
          const wordStartFrame = word.start * fps;
          const wordFrames = Math.max(0, frame - wordStartFrame);

          const wordSpring = spring({
            frame: wordFrames,
            fps,
            config: { stiffness: 250, damping: 16 },
          });

          const wordScale = interpolate(wordSpring, [0, 1], [0, 1]);
          const wordOpacity = interpolate(wordSpring, [0, 1], [0, 1]);

          const impact = isImpactWord(word.text);

          return (
            <span
              key={idx}
              style={{
                display: 'inline-block',
                fontSize: 68,
                fontWeight: 900,
                fontFamily: '"Arial Black", "Arial Bold", Impact, sans-serif',
                textTransform: 'uppercase',
                letterSpacing: '-0.02em',
                lineHeight: 1.1,
                transform: `scale(${wordScale})`,
                opacity: wordOpacity,
                color: impact ? '#FF1A1A' : '#FFFFFF',
                textShadow: impact
                  ? '0 0 30px rgba(255,0,0,0.9), 0 0 60px rgba(180,0,0,0.5), 0 4px 10px rgba(0,0,0,1)'
                  : '0 0 15px rgba(200,0,0,0.35), 0 4px 10px rgba(0,0,0,1)',
                WebkitTextStroke: impact
                  ? '1px rgba(255,80,80,0.4)'
                  : '1px rgba(255,255,255,0.08)',
                filter: impact
                  ? 'drop-shadow(0 0 8px rgba(255,0,0,0.6))'
                  : 'none',
              }}
            >
              {word.text}
            </span>
          );
        })}
      </div>

      {/* Bottom Blood-Red Accent Bar */}
      <div
        style={{
          marginTop: 10,
          height: 3,
          width: '55%',
          background:
            'linear-gradient(90deg, transparent, #CC0000, transparent)',
          opacity: accentOpacity,
          borderRadius: 2,
          boxShadow: '0 0 14px rgba(200,0,0,0.8), 0 0 4px rgba(255,0,0,1)',
        }}
      />
    </div>
  );
};

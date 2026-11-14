import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
export interface Subtitle {text: string; start: number; end: number}
export const Captions: React.FC<{subtitles: Subtitle[]; fps: number}> = ({subtitles, fps}) => {
  const seconds = useCurrentFrame() / fps;
  const {width, height} = useVideoConfig();
  const index = subtitles.findIndex(word => seconds >= word.start && seconds < word.end + 0.15);
  if (index < 0) return null;
  const first = Math.floor(index / 6) * 6;
  const text = subtitles.slice(first, first + 6).map(word => word.text).join(' ');
  return <div style={{position: 'absolute', left: '10%', right: '10%', bottom: height > width ? '18%' : '9%', textAlign: 'center', color: '#eee9e1', fontSize: height > width ? 46 : 38, lineHeight: 1.4, fontFamily: 'Arial, sans-serif', textShadow: '0 2px 8px #000', background: 'rgba(0,0,0,.5)', padding: '12px 20px', borderRadius: 6}}>{text}</div>;
};

import React from 'react';
import {Img, OffthreadVideo, Loop, interpolate, useCurrentFrame} from 'remotion';

export const AnimatedAsset: React.FC<{
  src: string;
  durationInFrames: number;
  animationType: string;
  mediaType?: string;
  videoFrames?: number;
}> = ({src, durationInFrames, mediaType, videoFrames = 150}) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, Math.max(1, durationInFrames)], [1, 1.06], {extrapolateRight: 'clamp'});
  return <div style={{position: 'absolute', inset: 0, overflow: 'hidden', background: '#08090b'}}>
    <div style={{width: '100%', height: '100%', transform: `scale(${scale})`, filter: 'brightness(0.65) contrast(1.15) grayscale(0.5)'}}>
      {mediaType === 'video' ? <Loop durationInFrames={Math.max(1, videoFrames)}>
        <OffthreadVideo src={src} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      </Loop> : <Img src={src} style={{width: '100%', height: '100%', objectFit: 'cover'}} />}
    </div>
    <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(circle, transparent 35%, rgba(0,0,0,.8) 100%)'}} />
  </div>;
};

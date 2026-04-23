import React from 'react';
import { Composition, getInputProps } from 'remotion';
import { Main } from './Main';
import './index.css';

export const RemotionRoot: React.FC = () => {
  const inputProps = getInputProps();
  
  // We can dynamically set the duration based on props if needed
  // For now, we'll default to 60 seconds (1800 frames at 30fps)
  const durationInFrames = 1800; 

  return (
    <>
      <Composition
        id="Shorts"
        component={Main}
        durationInFrames={durationInFrames}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={inputProps}
      />
      <Composition
        id="LongForm"
        component={Main}
        durationInFrames={durationInFrames}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={inputProps}
      />
    </>
  );
};

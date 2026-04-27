import React from 'react';
import {
  Sequence,
  Audio,
  staticFile,
  Series,
  useVideoConfig,
  getInputProps,
} from 'remotion';
import { AnimatedAsset } from './AnimatedAsset';
import { Captions, Subtitle } from './Captions';
import { TransitionOverlay } from './TransitionOverlay';
import { WaveformOverlay } from './WaveformOverlay';

interface Scene {
  text: string;
  image_url: string;
  sfx_url: string;
  animation_type: 'zoom' | 'pop' | 'slide_up' | 'slide_down' | 'fade';
  duration_estimate: number;
}

interface Props {
  title: string;
  scenes: Scene[];
  subtitles: Subtitle[];
  audio_url: string;
  atmosphere_url: string;
}

export const Main: React.FC = () => {
  const { fps, durationInFrames } = useVideoConfig();
  const inputProps = getInputProps() as Props;

  // Fallback props if none provided
  const props = inputProps.scenes ? inputProps : {
    title: "Horror Story",
    scenes: [],
    subtitles: [],
    audio_url: "",
    atmosphere_url: "",
    duration_in_frames: durationInFrames
  };

  // Calculate proportional durations to fit the actual audio length
  const totalEstimatedDuration = props.scenes.reduce((acc, s) => acc + (s.duration_estimate || 5), 0);
  const durationMultiplier = durationInFrames / (totalEstimatedDuration * fps);

  return (
    <div className="flex-1 bg-black">
      {/* 1. Background Music/Atmosphere */}
      {props.atmosphere_url && (
        <Audio src={staticFile(props.atmosphere_url)} volume={0.02} />
      )}

      {/* 2. Narration Audio */}
      {props.audio_url && (
        <Audio src={staticFile(props.audio_url)} />
      )}

      {/* 3. Visual Scenes */}
      <Series>
        {props.scenes.map((scene, index) => {
          const sceneDuration = Math.floor((scene.duration_estimate || 5) * fps * durationMultiplier);
          return (
            <Series.Sequence
              key={index}
              durationInFrames={sceneDuration}
            >
              <AnimatedAsset
                src={staticFile(scene.image_url)}
                durationInFrames={sceneDuration}
                animationType={scene.animation_type}
              />
              
              {/* Scene SFX */}
              {scene.sfx_url && (
                <Audio src={staticFile(scene.sfx_url)} volume={0.3} />
              )}
              
              {/* Transitions */}
              <Sequence durationInFrames={10}>
                <TransitionOverlay type="in" duration={10} />
              </Sequence>
              <Sequence from={sceneDuration - 10} durationInFrames={10}>
                <TransitionOverlay type="out" duration={10} />
              </Sequence>
            </Series.Sequence>
          );
        })}
      </Series>

      {/* 4. Captions Overlay */}
      <Captions subtitles={props.subtitles} fps={fps} />

      {/* 5. Waveform Visualization */}
      {props.audio_url && (
        <WaveformOverlay src={staticFile(props.audio_url)} />
      )}
    </div>
  );
};

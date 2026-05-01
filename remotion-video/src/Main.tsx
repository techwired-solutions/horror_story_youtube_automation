import React, { useMemo } from 'react';
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

interface Beat {
  text: string;
  image_url: string;
  sfx_url?: string;
  animation_type?: 'zoom' | 'pop' | 'slide_up' | 'slide_down' | 'fade';
  duration_estimate?: number;
}

interface Props {
  title: string;
  beats?: Beat[];
  scenes?: Beat[]; // fallback for old schema
  subtitles: Subtitle[];
  audio_url: string;
  atmosphere_url: string;
}

export const Main: React.FC = () => {
  const { fps, durationInFrames } = useVideoConfig();
  const inputProps = getInputProps() as Props;

  const props = {
    title: inputProps.title || "Horror Story",
    beats: inputProps.beats || inputProps.scenes || [],
    subtitles: inputProps.subtitles || [],
    audio_url: inputProps.audio_url || "",
    atmosphere_url: inputProps.atmosphere_url || "",
  };

  // Group contiguous beats with the same image_url into a single Visual Scene
  // to prevent animations from restarting every beat.
  const visualScenes = useMemo(() => {
    const scenes: any[] = [];
    let current = null;

    for (const beat of props.beats) {
      if (!current || current.image_url !== beat.image_url) {
        if (current) scenes.push(current);
        current = {
          image_url: beat.image_url,
          animation_type: beat.animation_type || 'zoom',
          duration_estimate: beat.duration_estimate || 2,
          sfx_urls: beat.sfx_url ? [beat.sfx_url] : [],
        };
      } else {
        current.duration_estimate += (beat.duration_estimate || 2);
        if (beat.sfx_url) current.sfx_urls.push(beat.sfx_url);
      }
    }
    if (current) scenes.push(current);
    return scenes;
  }, [props.beats]);

  const totalEstimatedDuration = visualScenes.reduce((acc, s) => acc + s.duration_estimate, 0) || 1;
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
        {visualScenes.map((scene, index) => {
          const sceneDuration = Math.floor((scene.duration_estimate) * fps * durationMultiplier);
          return (
            <Series.Sequence
              key={index}
              durationInFrames={Math.max(1, sceneDuration)}
            >
              {scene.image_url && (
                <AnimatedAsset
                  src={staticFile(scene.image_url)}
                  durationInFrames={sceneDuration}
                  animationType={scene.animation_type}
                />
              )}
              
              {/* Transitions */}
              <Sequence durationInFrames={10}>
                <TransitionOverlay type="in" duration={10} />
              </Sequence>
              <Sequence from={Math.max(0, sceneDuration - 10)} durationInFrames={10}>
                <TransitionOverlay type="out" duration={10} />
              </Sequence>
            </Series.Sequence>
          );
        })}
      </Series>

      {/* 4. Beat SFX Tracks */}
      {props.beats.map((beat, index) => {
        if (!beat.sfx_url) return null;
        const priorDuration = props.beats.slice(0, index).reduce((acc, b) => acc + (b.duration_estimate || 2), 0);
        const startFrame = Math.floor(priorDuration * fps * durationMultiplier);
        return (
          <Sequence key={`sfx-${index}`} from={startFrame}>
            <Audio src={staticFile(beat.sfx_url)} volume={0.3} />
          </Sequence>
        );
      })}

      {/* 5. Captions Overlay */}
      <Captions subtitles={props.subtitles} fps={fps} />

      {/* 6. Waveform Visualization */}
      {props.audio_url && (
        <WaveformOverlay src={staticFile(props.audio_url)} />
      )}
    </div>
  );
};

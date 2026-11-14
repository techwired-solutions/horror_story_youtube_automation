import React from 'react';
import {Audio, staticFile, Series, useVideoConfig, getInputProps, AbsoluteFill} from 'remotion';
import {AnimatedAsset} from './AnimatedAsset';
import {Captions, Subtitle} from './Captions';

interface Beat {
  image_url: string;
  media_type?: string;
  video_frames?: number;
  duration_estimate?: number;
}
interface Props {
  beats?: Beat[];
  subtitles?: Subtitle[];
  audio_url?: string;
  atmosphere_url?: string;
}
export const Main: React.FC = () => {
  const {fps, durationInFrames} = useVideoConfig();
  const props = getInputProps() as Props;
  const scenes: {src: string; kind?: string; videoFrames?: number; seconds: number}[] = [];
  for (const beat of props.beats || []) {
    const prior = scenes[scenes.length - 1];
    if (prior && prior.src === beat.image_url) prior.seconds += beat.duration_estimate || 8;
    else scenes.push({src: beat.image_url, kind: beat.media_type, videoFrames: beat.video_frames, seconds: beat.duration_estimate || 8});
  }
  const total = scenes.reduce((sum, scene) => sum + scene.seconds, 0) || 1;
  let accumulated = 0;
  let priorEnd = 0;
  return <AbsoluteFill style={{background: 'black'}}>
    {props.atmosphere_url && <Audio src={staticFile(props.atmosphere_url)} loop volume={0.025} />}
    {props.audio_url && <Audio src={staticFile(props.audio_url)} />}
    <Series>{scenes.map((scene, index) => {
      accumulated += scene.seconds;
      const end = index === scenes.length - 1 ? durationInFrames : Math.round(accumulated / total * durationInFrames);
      const frames = Math.max(1, end - priorEnd);
      priorEnd = end;
      return <Series.Sequence key={index} durationInFrames={frames}>
        <AnimatedAsset src={staticFile(scene.src)} durationInFrames={frames} animationType="zoom" mediaType={scene.kind} videoFrames={scene.videoFrames} />
      </Series.Sequence>;
    })}</Series>
    <Captions subtitles={props.subtitles || []} fps={fps} />
  </AbsoluteFill>;
};

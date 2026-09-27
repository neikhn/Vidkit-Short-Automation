import React from 'react';
import {Audio} from '@remotion/media';
import {AstraSoundTracks} from './AstraSoundTracks';
import {AstraVietnameseSoundTracks} from './AstraVietnameseSoundTracks';
import {Interactive, Sequence, staticFile, useVideoConfig, type InteractiveBaseProps, type InteractivitySchema, type SequenceControls} from 'remotion';

export type SoundTrack = {
  kind: 'sfx' | 'music';
  id: string; src: string; startMs: number; endMs: number; trimStartMs: number;
  gainDb: number; fadeInMs: number; fadeOutMs: number;
  envelope: Array<{atMs: number; db: number}>;
};

export const envelopeDb = (points: SoundTrack['envelope'], timeMs: number): number => {
  if (!points.length) return 0;
  if (timeMs <= points[0].atMs) return points[0].db;
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1];
    const b = points[i];
    if (timeMs <= b.atMs) {
      const progress = (timeMs - a.atMs) / Math.max(1, b.atMs - a.atMs);
      return a.db + (b.db - a.db) * progress;
    }
  }
  return points[points.length - 1].db;
};

type TrackProps = InteractiveBaseProps & {track: SoundTrack; volume: number};

const TrackInner: React.FC<TrackProps & {controls: SequenceControls | undefined}> = ({track, volume, controls, ...sequenceProps}) => {
  const {fps} = useVideoConfig();
    const from = Math.round(track.startMs * fps / 1000);
    const frames = Math.max(1, Math.round(track.endMs * fps / 1000) - from);
    const durationMs = frames * 1000 / fps;
    return <Sequence {...sequenceProps} controls={controls} from={sequenceProps.from ?? from} durationInFrames={sequenceProps.durationInFrames ?? frames}>
    <Audio
      src={staticFile(track.src)}
      trimBefore={Math.round(track.trimStartMs * fps / 1000)}
      volume={(frame) => {
        const localMs = frame * 1000 / fps;
        const fadeIn = track.fadeInMs ? Math.min(1, Math.max(0, localMs / track.fadeInMs)) : 1;
        const fadeOut = track.fadeOutMs ? Math.min(1, Math.max(0, (durationMs - localMs) / track.fadeOutMs)) : 1;
        const db = track.gainDb + envelopeDb(track.envelope, from * 1000 / fps + localMs);
        return volume * Math.pow(10, db / 20) * fadeIn * fadeOut;
      }}
      from={-2}
    />
    </Sequence>;
};

const trackSchema = {
  ...Interactive.baseSchema,
  volume: {type: 'number', default: 1, min: 0, max: 4, step: 0.05, hiddenFromList: false, description: 'Volume multiplier (1 = planned mix)', keyframable: true},
} as const satisfies InteractivitySchema;

const InteractiveTrack = Interactive.withSchema<typeof trackSchema, TrackProps>({
  Component: TrackInner,
  componentName: 'Sound track',
  schema: trackSchema,
  supportsEffects: false,
});

export const SoundTracks: React.FC<{tracks: SoundTrack[]}> = ({tracks}) => {
  if (tracks.some((track) => track.src?.includes('jobs/e5fb0399b313/') && track.id.startsWith('editorial-underscore'))) {
    return <AstraVietnameseSoundTracks />;
  }
  if (tracks.some((track) => track.src?.includes('jobs/0e00e47bb788/') && track.id.startsWith('editorial-underscore'))) {
    return <AstraSoundTracks />;
  }
  return <>{tracks.map((track) => {
    // Separate source locations keep Music visible outside Studio's duplicated SFX group.
    if (track.kind === 'music') {
      return <InteractiveTrack key={track.id} name={`Music · ${track.id}`} track={track} volume={1} />;
    }
    return <InteractiveTrack
      key={track.id}
      name={`SFX · ${track.id}`}
      track={track}
      volume={1.1}
    />;
  })}</>;
};

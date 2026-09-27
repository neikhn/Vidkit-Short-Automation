import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {VidkitShort, VidkitShortProps} from './VidkitShort';

export const defaultProps: VidkitShortProps = {
  schemaVersion: 2,
  language: 'vi',
  title: 'Vidkit preview',
  audioSrc: '',
  durationSeconds: 10,
  captions: [],
  scenes: [
    {
      id: 'scene-1',
      layout: 'hook',
      title: 'Vidkit preview',
      body: 'Truyền storyboard và timeline JSON để dựng video.',
      startMs: 0,
      endMs: 10000,
      status: 'provisional',
    },
  ],
  safeArea: {top: 88, right: 150, bottom: 260, left: 64},
};

export const calculateMetadata: CalculateMetadataFunction<VidkitShortProps> = ({props}) => ({
  durationInFrames: Math.max(1, Math.ceil(props.durationSeconds * 30)),
  props,
});

export const RemotionRoot: React.FC = () => (
  <Composition
    id="VidkitShort"
    component={VidkitShort}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={300}
    defaultProps={defaultProps}
    calculateMetadata={calculateMetadata}
  />
);

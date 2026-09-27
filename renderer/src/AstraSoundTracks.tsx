import React from 'react';
import {Audio} from '@remotion/media';
import {staticFile} from 'remotion';
// Authored clips: literal volume and timing stay editable in the Studio Inspector.
// Fades and narration ducking are baked into derived assets; originals are retained.
export const AstraSoundTracks: React.FC = () => <>
  <Audio name="Music - editorial-underscore" src={staticFile("jobs/0e00e47bb788/en/sound/05a44b410006e6da647e199686845edb254bd02e60a593da8ca6fd33d7c31864.wav")} from={0} durationInFrames={2244} trimBefore={0} volume={0.8} />
  <Audio name="SFX - astra-reveal" src={staticFile("jobs/0e00e47bb788/en/sound/63253e55fd12253854314e2379a94a707dadb20f1454bb866dc1e91550ebea99.wav")} from={12} durationInFrames={18} trimBefore={0} volume={0.88} />
  <Audio name="SFX - header-highlight" src={staticFile("jobs/0e00e47bb788/en/sound/720b3f60b396553e5cf035f50de4bd4434f2844fa8bd7e1de2a85dd309f11df6.wav")} from={93} durationInFrames={20} trimBefore={0} volume={0.88} />
  <Audio name="SFX - header-highlight-second" src={staticFile("jobs/0e00e47bb788/en/sound/720b3f60b396553e5cf035f50de4bd4434f2844fa8bd7e1de2a85dd309f11df6.wav")} from={126} durationInFrames={20} trimBefore={0} volume={0.88} />
  <Audio name="SFX - trace-connection" src={staticFile("jobs/0e00e47bb788/en/sound/720b3f60b396553e5cf035f50de4bd4434f2844fa8bd7e1de2a85dd309f11df6.wav")} from={487} durationInFrames={21} trimBefore={0} volume={0.88} />
  <Audio name="SFX - monitor-reveal" src={staticFile("jobs/0e00e47bb788/en/sound/63253e55fd12253854314e2379a94a707dadb20f1454bb866dc1e91550ebea99.wav")} from={657} durationInFrames={18} trimBefore={0} volume={0.88} />
  <Audio name="SFX - apollo-awareness" src={staticFile("jobs/0e00e47bb788/en/sound/63253e55fd12253854314e2379a94a707dadb20f1454bb866dc1e91550ebea99.wav")} from={967} durationInFrames={18} trimBefore={0} volume={0.88} />
  <Audio name="SFX - apollo-window" src={staticFile("jobs/0e00e47bb788/en/sound/720b3f60b396553e5cf035f50de4bd4434f2844fa8bd7e1de2a85dd309f11df6.wav")} from={1024} durationInFrames={20} trimBefore={0} volume={0.88} />
  <Audio name="SFX - apollo-limit" src={staticFile("jobs/0e00e47bb788/en/sound/63253e55fd12253854314e2379a94a707dadb20f1454bb866dc1e91550ebea99.wav")} from={1126} durationInFrames={18} trimBefore={0} volume={0.88} />
  <Audio name="SFX - cyber-scope" src={staticFile("jobs/0e00e47bb788/en/sound/720b3f60b396553e5cf035f50de4bd4434f2844fa8bd7e1de2a85dd309f11df6.wav")} from={1350} durationInFrames={20} trimBefore={0} volume={0.88} />
  <Audio name="SFX - math-monitor" src={staticFile("jobs/0e00e47bb788/en/sound/720b3f60b396553e5cf035f50de4bd4434f2844fa8bd7e1de2a85dd309f11df6.wav")} from={1606} durationInFrames={20} trimBefore={0} volume={0.88} />
  <Audio name="SFX - math-detected" src={staticFile("jobs/0e00e47bb788/en/sound/63253e55fd12253854314e2379a94a707dadb20f1454bb866dc1e91550ebea99.wav")} from={1641} durationInFrames={18} trimBefore={0} volume={0.88} />
  <Audio name="SFX - conclusion" src={staticFile("jobs/0e00e47bb788/en/sound/720b3f60b396553e5cf035f50de4bd4434f2844fa8bd7e1de2a85dd309f11df6.wav")} from={1840} durationInFrames={21} trimBefore={0} volume={0.88} />
  <Audio name="SFX - follow-cta" src={staticFile("jobs/0e00e47bb788/en/sound/63253e55fd12253854314e2379a94a707dadb20f1454bb866dc1e91550ebea99.wav")} from={2164} durationInFrames={18} trimBefore={0} volume={0.88} />
</>;

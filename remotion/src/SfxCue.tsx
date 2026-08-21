import React from "react";
import { Audio, Sequence } from "remotion";

interface Props {
  src: string;
  atFrame: number;
  volume?: number;
}

export const SfxCue: React.FC<Props> = ({ src, atFrame, volume = 0.5 }) => {
  if (!src) {
    return null;
  }

  return (
    <Sequence from={atFrame}>
      <Audio src={src} volume={volume} />
    </Sequence>
  );
};

import React from "react";
import { Audio, interpolate, useCurrentFrame } from "remotion";
import { SpeechRange } from "./Composition";

interface Props {
  src: string;
  speechRanges: SpeechRange[];
  baseVolume?: number;
  duckVolume?: number;
}

export const BackgroundAudio: React.FC<Props> = ({
  src,
  speechRanges = [],
  baseVolume = 0.14,
  duckVolume = 0.03
}) => {
  const frame = useCurrentFrame();

  if (!src) {
    return null;
  }

  // Cek apakah frame saat ini sedang berada dalam percakapan (+ padding 12 frame / 0.4s)
  const isSpeaking = speechRanges.some(
    (range) => frame >= range.start_frame - 8 && frame <= range.end_frame + 12
  );

  const targetVol = isSpeaking ? duckVolume : baseVolume;

  return (
    <Audio
      src={src}
      volume={(f) =>
        interpolate(
          f,
          [f - 6, f + 6],
          [targetVol, targetVol],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        )
      }
      loop
    />
  );
};

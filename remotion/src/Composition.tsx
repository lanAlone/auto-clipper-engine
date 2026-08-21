import React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile } from "remotion";
import { AnimatedCaption } from "./AnimatedCaption";
import { BackgroundAudio } from "./BackgroundAudio";
import { SfxCue } from "./SfxCue";

export interface CaptionWord {
  word: string;
  start_frame: number;
  end_frame: number;
  start_sec: number;
  end_sec: number;
}

export interface SpeechRange {
  start_frame: number;
  end_frame: number;
}

export interface SfxCueProps {
  file: string;
  at_frame: number;
  volume?: number;
}

export interface CompositionProps {
  clip_id: string;
  title: string;
  source_video: string;
  start_sec: number;
  end_sec: number;
  duration_frames: number;
  fps: number;
  width: number;
  height: number;
  crop_mode: "blurred_stack" | "center_crop";
  caption_style: "bold_yellow" | "clean_white" | "neon_cyan";
  captions: CaptionWord[];
  speech_ranges: SpeechRange[];
  backsound: {
    file: string | null;
    volume_base: number;
    duck_to: number;
  };
  sfx_cues: SfxCueProps[];
}

export const MainComposition: React.FC<CompositionProps> = ({
  source_video,
  start_sec,
  crop_mode = "blurred_stack",
  caption_style = "bold_yellow",
  captions = [],
  speech_ranges = [],
  backsound,
  sfx_cues = [],
  fps = 30
}) => {
  const startFromFrame = Math.round(start_sec * fps);

  return (
    <AbsoluteFill style={{ backgroundColor: "#060B18", overflow: "hidden" }}>
      {/* 1. LAYER VIDEO UTAMA */}
      {source_video && (
        <>
          {crop_mode === "blurred_stack" ? (
            <>
              {/* Background Layer: Scaled + Deep Blur */}
              <AbsoluteFill style={{ transform: "scale(1.3)", filter: "blur(32px) brightness(0.35) saturate(1.3)" }}>
                <OffthreadVideo
                  src={source_video}
                  startFrom={startFromFrame}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              </AbsoluteFill>

              {/* Foreground Layer: Crisp 16:9 Video Centered */}
              <AbsoluteFill
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "0 24px"
                }}
              >
                <div
                  style={{
                    width: "100%",
                    borderRadius: "20px",
                    overflow: "hidden",
                    boxShadow: "0 24px 60px rgba(0, 0, 0, 0.75)",
                    border: "1px solid rgba(255, 255, 255, 0.12)"
                  }}
                >
                  <OffthreadVideo
                    src={source_video}
                    startFrom={startFromFrame}
                    style={{ width: "100%", height: "auto", display: "block" }}
                  />
                </div>
              </AbsoluteFill>
            </>
          ) : (
            /* Center Crop Mode: Scaled to fill 9:16 viewport */
            <AbsoluteFill>
              <OffthreadVideo
                src={source_video}
                startFrom={startFromFrame}
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
            </AbsoluteFill>
          )}
        </>
      )}

      {/* 2. LAYER SUBTITLE KINETIK ANIMASI */}
      <AnimatedCaption captions={captions} captionStyle={caption_style} fps={fps} />

      {/* 3. LAYER AUDIO DUCKING & SFX */}
      {backsound?.file && (
        <BackgroundAudio
          src={backsound.file}
          speechRanges={speech_ranges}
          baseVolume={backsound.volume_base}
          duckVolume={backsound.duck_to}
        />
      )}

      {sfx_cues.map((cue, index) => (
        <SfxCue key={index} src={cue.file} atFrame={cue.at_frame} volume={cue.volume || 0.5} />
      ))}
    </AbsoluteFill>
  );
};

import React from "react";
import { Composition } from "remotion";
import { MainComposition, CompositionProps } from "./Composition";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Composition"
        component={MainComposition}
        durationInFrames={900}
        fps={30}
        width={1080}
        height={1920}
        calculateMetadata={({ props }) => {
          const compProps = props as CompositionProps;
          return {
            durationInFrames: compProps.duration_frames || 900,
            fps: compProps.fps || 30,
            width: compProps.width || 1080,
            height: compProps.height || 1920,
          };
        }}
        defaultProps={{
          clip_id: "c1",
          title: "Highlight Preview",
          source_video: "",
          start_sec: 0,
          end_sec: 30,
          duration_frames: 900,
          fps: 30,
          width: 1080,
          height: 1920,
          crop_mode: "blurred_stack",
          caption_style: "bold_yellow",
          captions: [],
          speech_ranges: [],
          backsound: { file: null, volume_base: 0.14, duck_to: 0.03 },
          sfx_cues: []
        } as CompositionProps}
      />
    </>
  );
};

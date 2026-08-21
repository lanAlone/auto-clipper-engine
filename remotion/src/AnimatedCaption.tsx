import React from "react";
import { useCurrentFrame, spring } from "remotion";
import { CaptionWord } from "./Composition";

interface Props {
  captions: CaptionWord[];
  captionStyle: "bold_yellow" | "clean_white" | "neon_cyan";
  fps: number;
}

export const AnimatedCaption: React.FC<Props> = ({ captions, captionStyle = "bold_yellow", fps = 30 }) => {
  const frame = useCurrentFrame();

  if (!captions || captions.length === 0) {
    return null;
  }

  // 1. Cari kata aktif pada frame saat ini
  const activeWordIndex = captions.findIndex(
    (w) => frame >= w.start_frame && frame <= w.end_frame + 4
  );

  if (activeWordIndex === -1) {
    return null;
  }

  // 2. Buat kelompok kalimat 3-4 kata di sekitar kata aktif (Chunking)
  const chunkSize = 4;
  const chunkStart = Math.floor(activeWordIndex / chunkSize) * chunkSize;
  const currentChunk = captions.slice(chunkStart, chunkStart + chunkSize);

  const activeWord = captions[activeWordIndex];

  // 3. Spring Animation untuk kata aktif
  const scale = spring({
    frame: frame - activeWord.start_frame,
    fps,
    config: {
      damping: 12,
      stiffness: 220,
      mass: 0.5
    }
  });

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: "22%", // 9:16 Safe Zone (bebas dari UI TikTok/Reels)
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        padding: "0 40px",
        pointerEvents: "none",
        zIndex: 50
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          alignItems: "center",
          gap: "14px",
          textAlign: "center",
          maxWidth: "960px",
          background: captionStyle === "clean_white" ? "rgba(0,0,0,0.65)" : "transparent",
          padding: captionStyle === "clean_white" ? "12px 24px" : "0",
          borderRadius: "16px"
        }}
      >
        {currentChunk.map((item, idx) => {
          const isCurrent = item.word === activeWord.word && item.start_frame === activeWord.start_frame;

          // Warna & Styling Sesuai Preset
          let activeColor = "#FFE600"; // Yellow
          let inactiveColor = "#FFFFFF";
          let strokeColor = "#000000";
          let textShadow = "0 8px 24px rgba(0,0,0,0.9)";

          if (captionStyle === "neon_cyan") {
            activeColor = "#38BDF8";
            inactiveColor = "#E2E8F0";
            textShadow = isCurrent ? "0 0 24px rgba(56, 189, 248, 0.9)" : "0 4px 12px rgba(0,0,0,0.8)";
          } else if (captionStyle === "clean_white") {
            activeColor = "#38BDF8";
            inactiveColor = "#94A3B8";
          }

          return (
            <span
              key={`${item.word}-${item.start_frame}-${idx}`}
              style={{
                fontFamily: "'Space Grotesk', 'Plus Jakarta Sans', sans-serif",
                fontSize: "58px",
                fontWeight: 800,
                textTransform: "uppercase",
                letterSpacing: "-0.01em",
                color: isCurrent ? activeColor : inactiveColor,
                WebkitTextStroke: captionStyle !== "clean_white" ? `8px ${strokeColor}` : "none",
                paintOrder: "stroke fill",
                textShadow,
                transform: isCurrent ? `scale(${Math.max(1, scale)})` : "scale(1)",
                display: "inline-block",
                transition: "color 0.1s ease"
              }}
            >
              {item.word}
            </span>
          );
        })}
      </div>
    </div>
  );
};

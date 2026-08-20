import type { BackgroundDefinition } from "@/lib/content/backgrounds";

/**
 * Decorative motif drawn on top of the background gradient.
 *
 * Everything is plain CSS/SVG so it survives the html-to-image export and
 * contains no text — the Persian headline is always a separate layer (§5.6).
 */
export function BackgroundLayer({
  background,
  sceneUrl,
}: {
  background: BackgroundDefinition;
  sceneUrl?: string | null;
}) {
  if (sceneUrl) {
    return (
      <div className="absolute inset-0" aria-hidden="true">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={sceneUrl}
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(to top, rgba(0,0,0,0.22), rgba(0,0,0,0) 45%)",
          }}
        />
      </div>
    );
  }

  return (
    <div
      className="absolute inset-0"
      style={{ background: background.css }}
      aria-hidden="true"
    >
      <Motif background={background} />
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(to top, rgba(0,0,0,0.22), rgba(0,0,0,0) 45%)",
        }}
      />
    </div>
  );
}

function Motif({ background }: { background: BackgroundDefinition }) {
  const accent = background.accent_color;

  switch (background.motif) {
    case "glow":
      return (
        <>
          <div
            className="absolute"
            style={{
              insetInlineEnd: "-15%",
              top: "-12%",
              width: "70%",
              height: "45%",
              background: `radial-gradient(circle, ${accent}44 0%, transparent 70%)`,
            }}
          />
          <div
            className="absolute"
            style={{
              insetInlineStart: "-20%",
              bottom: "-10%",
              width: "65%",
              height: "40%",
              background: `radial-gradient(circle, ${accent}22 0%, transparent 70%)`,
            }}
          />
        </>
      );

    case "rays":
      return (
        <div
          className="absolute inset-0"
          style={{
            opacity: 0.24,
            background: `conic-gradient(from 200deg at 70% 0%, transparent 0deg, ${accent}66 25deg, transparent 55deg, ${accent}44 90deg, transparent 130deg)`,
          }}
        />
      );

    case "grain":
      return (
        <div
          className="absolute inset-0"
          style={{
            opacity: 0.5,
            backgroundImage: `radial-gradient(${accent}26 1px, transparent 1px)`,
            backgroundSize: "8px 8px",
          }}
        />
      );

    case "grid":
      return (
        <div
          className="absolute inset-0"
          style={{
            opacity: 0.35,
            backgroundImage: `linear-gradient(${accent}1f 1px, transparent 1px), linear-gradient(90deg, ${accent}1f 1px, transparent 1px)`,
            backgroundSize: "9% 7%",
          }}
        />
      );

    case "blobs":
      return (
        <>
          <div
            className="absolute rounded-full"
            style={{
              insetInlineStart: "-14%",
              top: "8%",
              width: "52%",
              aspectRatio: "1",
              background: `${accent}33`,
              filter: "blur(6px)",
            }}
          />
          <div
            className="absolute rounded-full"
            style={{
              insetInlineEnd: "-10%",
              bottom: "12%",
              width: "40%",
              aspectRatio: "1",
              background: "rgba(255,255,255,0.22)",
              filter: "blur(4px)",
            }}
          />
        </>
      );

    case "arch":
      return (
        <svg
          className="absolute inset-0 h-full w-full"
          viewBox="0 0 100 125"
          preserveAspectRatio="none"
        >
          <path
            d="M50 12c16 0 28 12 28 28v70H22V40c0-16 12-28 28-28z"
            fill="none"
            stroke={accent}
            strokeOpacity="0.45"
            strokeWidth="0.6"
          />
          <path
            d="M50 20c12 0 21 9 21 21v69H29V41c0-12 9-21 21-21z"
            fill="none"
            stroke={accent}
            strokeOpacity="0.25"
            strokeWidth="0.4"
          />
          <g stroke={accent} strokeOpacity="0.3" strokeWidth="0.4" fill="none">
            <path d="M50 6 54 10 50 14 46 10z" />
            <path d="M14 60 18 64 14 68 10 64z" />
            <path d="M86 60 90 64 86 68 82 64z" />
          </g>
        </svg>
      );

    default:
      return null;
  }
}

import type { CSSProperties } from "react";
import type { TextLayer } from "@/types/domain";
import { fontFamilyCss } from "./fonts";

export function textLayerBoxStyle(layer: TextLayer): CSSProperties {
  return {
    position: "absolute",
    left: `${layer.x * 100}%`,
    top: `${layer.y * 100}%`,
    width: `${layer.width * 100}%`,
    fontFamily: fontFamilyCss(layer.font_family),
    fontSize: `${layer.font_size * 100}cqw`,
    fontWeight: layer.font_weight,
    color: layer.color,
    textAlign: layer.text_align,
    opacity: layer.opacity,
    lineHeight: 1.45,
    textWrap: "balance",
    whiteSpace: "pre-wrap",
    overflowWrap: "anywhere",
    pointerEvents: "none",
    textShadow: layer.shadow ? "0 2px 12px rgba(0,0,0,0.18)" : "none",
  };
}

export function textLayerFillStyle(layer: TextLayer): CSSProperties | undefined {
  if (layer.background === "none" || !layer.background_color) return undefined;
  const alpha = layer.background_opacity;
  return {
    display: "inline-block",
    maxWidth: "100%",
    backgroundColor: hexToRgba(layer.background_color, alpha),
    color: "inherit",
    borderRadius: layer.background === "pill" ? "999px" : "0.35em",
    paddingInline: layer.background === "pill" ? "0.7em" : "0.45em",
    paddingBlock: layer.background === "pill" ? "0.28em" : "0.2em",
    lineHeight: 1.6,
  };
}

export function TextLayerView({ layer }: { layer: TextLayer }) {
  if (!layer.text) return null;
  const fill = textLayerFillStyle(layer);
  return (
    <div style={textLayerBoxStyle(layer)} data-text-layer={layer.id}>
      {fill ? <span style={fill}>{layer.text}</span> : layer.text}
    </div>
  );
}

function hexToRgba(hex: string, alpha: number): string {
  const normalized =
    hex.length === 4
      ? `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`
      : hex;
  const value = Number.parseInt(normalized.slice(1), 16);
  const r = (value >> 16) & 255;
  const g = (value >> 8) & 255;
  const b = value & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

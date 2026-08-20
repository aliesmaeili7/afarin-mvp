import { toPng } from "html-to-image";
import { AD_FONTS } from "./fonts";

/**
 * PNG export of a composed ad.
 *
 * Persian text is the fragile part of DOM-to-image conversion, so every catalog
 * face is inlined as a data URL and the capture waits for both
 * `document.fonts.ready` and every <img> in the subtree before rasterising.
 */

let fontEmbedCssPromise: Promise<string> | null = null;

async function toBase64(response: Response): Promise<string> {
  const buffer = await response.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize));
  }
  return btoa(binary);
}

function mimeFor(format: "woff2" | "truetype"): string {
  return format === "truetype" ? "font/ttf" : "font/woff2";
}

export function getFontEmbedCss(): Promise<string> {
  fontEmbedCssPromise ??= (async () => {
    const faces = await Promise.all(
      AD_FONTS.flatMap((font) =>
        font.faces.map(async (face) => {
          const response = await fetch(face.path);
          if (!response.ok) return "";
          const base64 = await toBase64(response);
          return [
            "@font-face {",
            `  font-family: "${font.family}";`,
            "  font-style: normal;",
            `  font-weight: ${face.weight};`,
            "  font-display: block;",
            `  src: url(data:${mimeFor(face.format)};base64,${base64}) format("${face.format}");`,
            "}",
          ].join("\n");
        }),
      ),
    );
    return faces.filter(Boolean).join("\n");
  })();

  return fontEmbedCssPromise;
}

async function waitForImages(node: HTMLElement): Promise<void> {
  const images = Array.from(node.querySelectorAll("img"));
  await Promise.all(
    images.map((image) => {
      if (image.complete && image.naturalWidth > 0) return Promise.resolve();
      return new Promise<void>((resolve) => {
        image.addEventListener("load", () => resolve(), { once: true });
        image.addEventListener("error", () => resolve(), { once: true });
      });
    }),
  );
}

export async function renderNodeToPng(
  node: HTMLElement,
  targetWidth: number,
): Promise<string> {
  const [fontEmbedCSS] = await Promise.all([
    getFontEmbedCss(),
    document.fonts.ready,
    waitForImages(node),
  ]);

  const currentWidth = node.offsetWidth || targetWidth;

  return toPng(node, {
    pixelRatio: targetWidth / currentWidth,
    cacheBust: true,
    fontEmbedCSS,
  });
}

export function downloadDataUrl(dataUrl: string, filename: string): void {
  const link = document.createElement("a");
  link.download = filename;
  link.href = dataUrl;
  link.click();
}

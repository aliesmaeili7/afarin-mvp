import { toPng } from "html-to-image";

/**
 * PNG export of a composed ad.
 *
 * Persian text is the fragile part of DOM-to-image conversion, so the font is
 * inlined as a data URL and the capture waits for both `document.fonts.ready`
 * and every <img> in the subtree before rasterising.
 */

const FONT_FILES = [
  "/fonts/vazirmatn-arabic-wght-normal.woff2",
  "/fonts/vazirmatn-latin-wght-normal.woff2",
];

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

export function getFontEmbedCss(): Promise<string> {
  fontEmbedCssPromise ??= (async () => {
    const faces = await Promise.all(
      FONT_FILES.map(async (path) => {
        const response = await fetch(path);
        if (!response.ok) return "";
        const base64 = await toBase64(response);
        return [
          "@font-face {",
          '  font-family: "Vazirmatn";',
          "  font-style: normal;",
          "  font-weight: 100 900;",
          "  font-display: block;",
          `  src: url(data:font/woff2;base64,${base64}) format("woff2");`,
          "}",
        ].join("\n");
      }),
    );
    return faces.join("\n");
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

"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { AssetRenderSpec } from "@/types/domain";
import { AdCanvas } from "./AdCanvas";
import { downloadDataUrl, renderNodeToPng } from "./exportAsset";

interface ExportRequest {
  spec: AssetRenderSpec;
  width: number;
  height: number;
  filename: string;
}

interface AssetExportContextValue {
  exportAsset: (request: ExportRequest) => Promise<void>;
  exporting: boolean;
}

const AssetExportContext = createContext<AssetExportContextValue | null>(null);

export function useAssetExport(): AssetExportContextValue {
  const context = useContext(AssetExportContext);
  if (!context) {
    throw new Error("useAssetExport must be used inside <AssetExportProvider>");
  }
  return context;
}

const STAGE_WIDTH = 540;

/**
 * Exports always run against a hidden, fixed-width copy of the ad rather than
 * whatever size it happens to be on screen, so a thumbnail and a full preview
 * produce byte-for-byte comparable downloads.
 */
export function AssetExportProvider({ children }: { children: ReactNode }) {
  const [request, setRequest] = useState<ExportRequest | null>(null);
  const [exporting, setExporting] = useState(false);
  const stageRef = useRef<HTMLDivElement | null>(null);

  const exportAsset = useCallback(async (next: ExportRequest) => {
    setExporting(true);
    setRequest(next);
    try {
      // Let React paint the hidden stage before rasterising it.
      await new Promise((resolve) => requestAnimationFrame(() => resolve(null)));
      await new Promise((resolve) => requestAnimationFrame(() => resolve(null)));

      const node = stageRef.current;
      if (!node) throw new Error("export stage is not mounted");

      const dataUrl = await renderNodeToPng(node, next.width);
      downloadDataUrl(dataUrl, next.filename);
    } finally {
      setExporting(false);
      setRequest(null);
    }
  }, []);

  const value = useMemo(() => ({ exportAsset, exporting }), [exportAsset, exporting]);

  return (
    <AssetExportContext.Provider value={value}>
      {children}
      <div
        aria-hidden="true"
        style={{
          position: "fixed",
          insetInlineStart: "-10000px",
          top: 0,
          width: STAGE_WIDTH,
          pointerEvents: "none",
          opacity: 0,
        }}
      >
        {request ? (
          <AdCanvas
            innerRef={stageRef}
            spec={request.spec}
            width={request.width}
            height={request.height}
          />
        ) : null}
      </div>
    </AssetExportContext.Provider>
  );
}

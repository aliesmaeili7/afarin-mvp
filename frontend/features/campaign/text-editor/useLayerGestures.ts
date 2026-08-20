import { useCallback, useEffect, useRef, useState } from "react";
import type { TextLayer } from "@/types/domain";
import { clampLayer, stageTouchAction } from "@/features/campaign/ad-renderer/textLayers";

interface GestureArgs {
  layers: TextLayer[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onLiveChange: (layers: TextLayer[]) => void;
  onCommit: (layers: TextLayer[]) => void;
}

function clientToNorm(
  event: Pick<PointerEvent, "clientX" | "clientY">,
  canvas: HTMLElement,
): { x: number; y: number } {
  const rect = canvas.getBoundingClientRect();
  return {
    x: rect.width ? (event.clientX - rect.left) / rect.width : 0,
    y: rect.height ? (event.clientY - rect.top) / rect.height : 0,
  };
}

function updateLayer(layers: TextLayer[], id: string, patch: Partial<TextLayer>): TextLayer[] {
  return layers.map((layer) =>
    layer.id === id ? clampLayer({ ...layer, ...patch }) : layer,
  );
}

/**
 * Pointer drag + corner resize + optional two-finger pinch. touch-action is
 * none only while a gesture is active so the page can still scroll outside.
 */
export function useLayerGestures({
  layers,
  selectedId,
  onSelect,
  onLiveChange,
  onCommit,
}: GestureArgs) {
  const layersRef = useRef(layers);
  const selectedRef = useRef(selectedId);

  useEffect(() => {
    layersRef.current = layers;
  }, [layers]);
  useEffect(() => {
    selectedRef.current = selectedId;
  }, [selectedId]);

  const dragRef = useRef<{
    id: string;
    mode: "move" | "resize" | "pinch";
    originX: number;
    originY: number;
    start: TextLayer;
    pointerId: number;
    second?: { pointerId: number; distance: number; fontSize: number };
  } | null>(null);
  const [interacting, setInteracting] = useState(false);

  const finish = useCallback(() => {
    const drag = dragRef.current;
    dragRef.current = null;
    setInteracting(false);
    if (!drag) return;
    onCommit(layersRef.current);
  }, [onCommit]);

  const onPointerDown = useCallback(
    (event: React.PointerEvent<HTMLElement>, id: string, mode: "move" | "resize") => {
      event.preventDefault();
      event.stopPropagation();
      const canvas = event.currentTarget.closest("[data-editor-stage]") as HTMLElement | null;
      if (!canvas) return;
      const current = layersRef.current.find((layer) => layer.id === id);
      if (!current) return;
      onSelect(id);
      const point = clientToNorm(event.nativeEvent, canvas);
      setInteracting(true);
      dragRef.current = {
        id,
        mode,
        originX: point.x,
        originY: point.y,
        start: current,
        pointerId: event.pointerId,
      };
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [onSelect],
  );

  const onStagePointerDown = useCallback(
    (event: React.PointerEvent<HTMLElement>) => {
      const target = event.target as HTMLElement;
      if (target.closest("[data-layer-hit]")) return;
      onSelect(null);
    },
    [onSelect],
  );

  const onPointerMove = useCallback(
    (event: React.PointerEvent<HTMLElement>) => {
      const drag = dragRef.current;
      if (!drag) return;
      const canvas = event.currentTarget.closest("[data-editor-stage]") as HTMLElement | null;
      if (!canvas) return;

      if (drag.mode === "pinch" && drag.second && event.pointerId === drag.second.pointerId) {
        return;
      }

      event.preventDefault();
      const point = clientToNorm(event.nativeEvent, canvas);

      if (drag.mode === "resize") {
        const delta = Math.max(point.x - drag.originX, point.y - drag.originY);
        const nextSize = drag.start.font_size + delta * 0.35;
        onLiveChange(
          updateLayer(layersRef.current, drag.id, {
            font_size: nextSize,
            width: Math.max(0.12, drag.start.width + delta),
          }),
        );
        return;
      }

      onLiveChange(
        updateLayer(layersRef.current, drag.id, {
          x: drag.start.x + (point.x - drag.originX),
          y: drag.start.y + (point.y - drag.originY),
        }),
      );
    },
    [onLiveChange],
  );

  const onPointerUp = useCallback(
    (event: React.PointerEvent<HTMLElement>) => {
      if (!dragRef.current) return;
      if (event.pointerId !== dragRef.current.pointerId && event.pointerId !== dragRef.current.second?.pointerId) {
        return;
      }
      finish();
    },
    [finish],
  );

  const onTouchStart = useCallback(
    (event: React.TouchEvent<HTMLElement>) => {
      if (event.touches.length !== 2 || !selectedRef.current) return;
      const [first, second] = [event.touches[0], event.touches[1]];
      const current = layersRef.current.find((layer) => layer.id === selectedRef.current);
      if (!current) return;
      event.preventDefault();
      setInteracting(true);
      const distance = Math.hypot(second.clientX - first.clientX, second.clientY - first.clientY);
      dragRef.current = {
        id: current.id,
        mode: "pinch",
        originX: 0,
        originY: 0,
        start: current,
        pointerId: -1,
        second: { pointerId: -2, distance, fontSize: current.font_size },
      };
    },
    [],
  );

  const onTouchMove = useCallback(
    (event: React.TouchEvent<HTMLElement>) => {
      const drag = dragRef.current;
      if (!drag || drag.mode !== "pinch" || !drag.second || event.touches.length !== 2) return;
      event.preventDefault();
      const [first, second] = [event.touches[0], event.touches[1]];
      const distance = Math.hypot(second.clientX - first.clientX, second.clientY - first.clientY);
      const scale = distance / (drag.second.distance || 1);
      onLiveChange(
        updateLayer(layersRef.current, drag.id, {
          font_size: drag.second.fontSize * scale,
        }),
      );
    },
    [onLiveChange],
  );

  const onTouchEnd = useCallback(
    (event: React.TouchEvent<HTMLElement>) => {
      if (dragRef.current?.mode === "pinch" && event.touches.length < 2) {
        finish();
      }
    },
    [finish],
  );

  return {
    interacting,
    touchAction: stageTouchAction(interacting),
    onPointerDown,
    onStagePointerDown,
    onPointerMove,
    onPointerUp,
    onTouchStart,
    onTouchMove,
    onTouchEnd,
  };
}

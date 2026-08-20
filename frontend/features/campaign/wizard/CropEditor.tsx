"use client";

import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import type { CropRect } from "@/types/domain";
import { type CropHandle, resizeCrop } from "./cropMath";

const HANDLES: CropHandle[] = ["nw", "ne", "sw", "se"];

export function CropEditor({
  src,
  crop,
  onChange,
  onCommit,
}: {
  src: string;
  crop: CropRect;
  onChange: (crop: CropRect) => void;
  onCommit?: (crop: CropRect) => void;
}) {
  const frameRef = useRef<HTMLDivElement>(null);
  const [drag, setDrag] = useState<{
    handle: CropHandle;
    startX: number;
    startY: number;
    origin: CropRect;
  } | null>(null);

  function pointFromClient(clientX: number, clientY: number) {
    const box = frameRef.current?.getBoundingClientRect();
    if (!box || box.width === 0 || box.height === 0) return { x: 0, y: 0 };
    return {
      x: (clientX - box.left) / box.width,
      y: (clientY - box.top) / box.height,
    };
  }

  function begin(handle: CropHandle, event: ReactPointerEvent) {
    event.preventDefault();
    event.stopPropagation();
    const at = pointFromClient(event.clientX, event.clientY);
    setDrag({ handle, startX: at.x, startY: at.y, origin: crop });
  }

  useEffect(() => {
    if (!drag) return;
    const active = drag;
    let latest = active.origin;

    function onMove(event: PointerEvent) {
      event.preventDefault();
      const box = frameRef.current?.getBoundingClientRect();
      if (!box || box.width === 0 || box.height === 0) return;
      const x = (event.clientX - box.left) / box.width;
      const y = (event.clientY - box.top) / box.height;
      latest = resizeCrop(
        active.origin,
        active.handle,
        x - active.startX,
        y - active.startY,
      );
      onChange(latest);
    }

    function onUp() {
      setDrag(null);
      onCommit?.(latest);
    }

    window.addEventListener("pointermove", onMove, { passive: false });
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
    };
  }, [drag, onChange, onCommit]);

  return (
    <div className="flex flex-col gap-3">
      <div
        ref={frameRef}
        className="relative w-full overflow-hidden rounded-3xl bg-ink-900 touch-none select-none"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt="کادر محصول"
          className="pointer-events-none block h-auto w-full"
          draggable={false}
        />
        <div
          role="presentation"
          className="absolute cursor-move border-2 border-white shadow-[0_0_0_9999px_rgba(15,11,22,0.55)]"
          style={{
            left: `${crop.x * 100}%`,
            top: `${crop.y * 100}%`,
            width: `${crop.width * 100}%`,
            height: `${crop.height * 100}%`,
            touchAction: "none",
          }}
          onPointerDown={(event) => begin("move", event)}
        >
          {HANDLES.map((handle) => (
            <button
              key={handle}
              type="button"
              aria-label="تغییر اندازه کادر"
              className={`absolute z-10 size-8 rounded-full border-2 border-white bg-brand-500 ${
                handle.startsWith("n") ? "top-0 -translate-y-1/2" : "bottom-0 translate-y-1/2"
              } ${
                handle.endsWith("w")
                  ? "left-0 -translate-x-1/2"
                  : "right-0 translate-x-1/2"
              }`}
              onPointerDown={(event) => {
                event.stopPropagation();
                begin(handle, event);
              }}
            />
          ))}
        </div>
      </div>
      <p className="text-sm leading-7 text-ink-500">
        کادر رو دور خود محصول بکش تا نوار اینستاگرام و حاشیه‌ها تو تبلیغ نیاد. با
        انگشت جابه‌جا یا بزرگش کن.
      </p>
    </div>
  );
}

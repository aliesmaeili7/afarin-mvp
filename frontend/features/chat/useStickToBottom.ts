"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export function useStickToBottom(
  deps: unknown[],
): {
  scrollerRef: React.RefObject<HTMLDivElement | null>;
  onScroll: () => void;
  showJump: boolean;
  jumpToLatest: () => void;
  pinToBottom: () => void;
} {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const stickRef = useRef(true);
  const [showJump, setShowJump] = useState(false);

  const onScroll = useCallback(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    const nearBottom = distance < 96;
    stickRef.current = nearBottom;
    setShowJump(!nearBottom);
  }, []);

  const jumpToLatest = useCallback(() => {
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
    stickRef.current = true;
    setShowJump(false);
  }, []);

  const pinToBottom = useCallback(() => {
    stickRef.current = true;
    jumpToLatest();
  }, [jumpToLatest]);

  useEffect(() => {
    if (!stickRef.current) return;
    jumpToLatest();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { scrollerRef, onScroll, showJump, jumpToLatest, pinToBottom };
}

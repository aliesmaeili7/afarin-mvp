"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Legacy Smart/Custom visual step. The Director flow lives on /create/directions. */
export function VisualStep() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/create/directions");
  }, [router]);
  return null;
}

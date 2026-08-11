"use client";

import { useState, type Dispatch, type SetStateAction } from "react";

/**
 * Seeds a form from server data exactly once per record.
 *
 * Uses React's "adjust state while rendering" pattern rather than an effect, so
 * a later refetch never clobbers something the user is in the middle of typing.
 */
export function useHydratedForm<T>(
  recordKey: string | null,
  build: () => T,
  initial: T,
): [T, Dispatch<SetStateAction<T>>] {
  const [value, setValue] = useState<T>(initial);
  const [hydratedKey, setHydratedKey] = useState<string | null>(null);

  if (recordKey !== null && recordKey !== hydratedKey) {
    setHydratedKey(recordKey);
    setValue(build());
  }

  return [value, setValue];
}

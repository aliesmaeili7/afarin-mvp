/** Simulated round-trip times so loading states are exercised honestly. */
export const LATENCY = {
  read: 160,
  write: 280,
  upload: 700,
  concepts: 1800,
  auth: 800,
} as const;

export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export type MockFailureMode = "off" | "generation" | "partial";

const FAILURE_KEY = "afarin.mock_failure";

/**
 * Dev-only switch for exercising the failure UIs. Set from the console:
 *   localStorage.setItem('afarin.mock_failure', 'partial')
 */
export function getFailureMode(): MockFailureMode {
  if (typeof localStorage === "undefined") return "off";
  const value = localStorage.getItem(FAILURE_KEY);
  return value === "generation" || value === "partial" ? value : "off";
}

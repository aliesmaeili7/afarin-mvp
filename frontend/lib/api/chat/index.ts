import { mockChatApi } from "./mockChatApi";
import { httpChatApi } from "./httpChatApi";
import type { ChatApi } from "./types";

/**
 * Same switch as the rest of Afarin: NEXT_PUBLIC_API_MODE=http talks to FastAPI.
 * Default remains the Phase A in-memory mock so the UI stays demoable offline.
 */
export const chatApiMode = process.env.NEXT_PUBLIC_API_MODE ?? "mock";

function createChatApi(): ChatApi {
  switch (chatApiMode) {
    case "http":
      return httpChatApi;
    case "mock":
    default:
      return mockChatApi;
  }
}

export const chatApi: ChatApi = createChatApi();
export type { ChatApi } from "./types";
export * from "./types";

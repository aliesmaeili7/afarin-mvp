import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { chatApi } from "@/lib/api/chat";

function walk(dir: string): string[] {
  const entries = readdirSync(dir);
  const files: string[] = [];
  for (const name of entries) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) files.push(...walk(path));
    else if (path.endsWith(".ts") || path.endsWith(".tsx")) files.push(path);
  }
  return files;
}

function chatUiSources(): string[] {
  const root = dirname(fileURLToPath(import.meta.url));
  return walk(root).filter(
    (path) =>
      !path.endsWith(".test.ts") && !path.includes("/lib/api/chat/"),
  );
}

describe("ChatApi boundary", () => {
  it("exposes conversation management on ChatApi", () => {
    expect(typeof chatApi.renameConversation).toBe("function");
    expect(typeof chatApi.deleteConversation).toBe("function");
    expect(typeof chatApi.archiveConversation).toBe("function");
    expect(typeof chatApi.restoreConversation).toBe("function");
    expect(typeof chatApi.pinConversation).toBe("function");
    expect(typeof chatApi.unpinConversation).toBe("function");
    expect(typeof chatApi.shareConversation).toBe("function");
    expect(typeof chatApi.searchConversations).toBe("function");
    expect(typeof chatApi.sendMessage).toBe("function");
  });

  it("keeps chat UI off the mock storage internals", () => {
    const forbidden = [
      "createSeedConversations",
      "resetChatMock",
      "from \"./mockChatData\"",
      "from \"@/lib/api/chat/mockChatData\"",
    ];
    for (const file of chatUiSources()) {
      const source = readFileSync(file, "utf8");
      for (const needle of forbidden) {
        expect(source, `${file} contains ${needle}`).not.toContain(needle);
      }
    }
  });

  it("keeps chat UI off campaign, education, and supabase", () => {
    const forbidden = [
      "features/campaign",
      "features/education",
      "@/lib/supabase",
      "lib/api/http",
      "lib/api/mock",
    ];
    for (const file of chatUiSources()) {
      const source = readFileSync(file, "utf8");
      for (const needle of forbidden) {
        expect(source, `${file} contains ${needle}`).not.toContain(needle);
      }
    }
  });
});

import { describe, expect, it } from "vitest";
import { detectCoarsePointer, shouldSendOnEnter } from "./composerKeys";

describe("composer keys", () => {
  it("sends on Enter for a fine pointer", () => {
    expect(shouldSendOnEnter({ key: "Enter", shiftKey: false }, false)).toBe(
      true,
    );
  });

  it("inserts a newline with Shift+Enter", () => {
    expect(shouldSendOnEnter({ key: "Enter", shiftKey: true }, false)).toBe(
      false,
    );
  });

  it("does not send on Enter for a coarse pointer", () => {
    expect(shouldSendOnEnter({ key: "Enter", shiftKey: false }, true)).toBe(
      false,
    );
  });

  it("ignores IME composition", () => {
    expect(
      shouldSendOnEnter(
        { key: "Enter", shiftKey: false, isComposing: true },
        false,
      ),
    ).toBe(false);
  });

  it("reads coarse pointer from a media query", () => {
    expect(detectCoarsePointer({ matches: true })).toBe(true);
    expect(detectCoarsePointer({ matches: false })).toBe(false);
    expect(detectCoarsePointer(null)).toBe(false);
  });
});

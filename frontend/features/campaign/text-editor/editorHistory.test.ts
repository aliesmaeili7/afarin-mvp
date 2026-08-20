import { describe, expect, it } from "vitest";
import {
  canRedo,
  canUndo,
  createHistory,
  HISTORY_LIMIT,
  pushHistory,
  redoHistory,
  undoHistory,
} from "./editorHistory";

describe("editorHistory", () => {
  it("undoes and redoes snapshots", () => {
    let state = createHistory("a");
    state = pushHistory(state, "b");
    state = pushHistory(state, "c");
    expect(state.present).toBe("c");
    state = undoHistory(state);
    expect(state.present).toBe("b");
    expect(canUndo(state)).toBe(true);
    state = redoHistory(state);
    expect(state.present).toBe("c");
    expect(canRedo(state)).toBe(false);
  });

  it("caps the past at HISTORY_LIMIT", () => {
    let state = createHistory(0);
    for (let index = 1; index <= HISTORY_LIMIT + 8; index += 1) {
      state = pushHistory(state, index);
    }
    expect(state.past.length).toBe(HISTORY_LIMIT);
    expect(state.present).toBe(HISTORY_LIMIT + 8);
  });
});

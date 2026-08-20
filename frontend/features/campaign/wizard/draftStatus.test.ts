import { describe, expect, it } from "vitest";
import { isWizardDraft } from "./draftStatus";

describe("isWizardDraft", () => {
  it("allows in-progress wizard campaigns and rejects finished ones", () => {
    expect(isWizardDraft("draft")).toBe(true);
    expect(isWizardDraft("brief_complete")).toBe(true);
    expect(isWizardDraft("concepts_ready")).toBe(true);
    expect(isWizardDraft("concept_selected")).toBe(true);
    expect(isWizardDraft("candidates_ready")).toBe(false);
    expect(isWizardDraft("ready")).toBe(false);
    expect(isWizardDraft("queued")).toBe(false);
    expect(isWizardDraft("generating")).toBe(false);
    expect(isWizardDraft("failed")).toBe(false);
  });
});

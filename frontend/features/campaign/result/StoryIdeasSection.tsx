"use client";

import { track } from "@/lib/analytics/track";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { CopyIcon } from "@/components/ui/icons";
import { toPersianDigits } from "@/lib/format/persian";
import { useClipboard } from "@/lib/hooks/useClipboard";
import type { CampaignCopy } from "@/types/domain";
import { SectionHeading } from "./AssetSection";

/** Spec §16 section 5 — three short Story texts with a copy button. */
export function StoryIdeasSection({ copies }: { copies: CampaignCopy[] }) {
  const copy = useClipboard();
  const stories = copies.filter((item) => item.copy_type === "story");

  if (stories.length === 0) return null;

  return (
    <section>
      <SectionHeading
        title="ایده‌های استوری"
        description="متن‌های کوتاه برای استوری روزانه."
      />
      <div className="flex flex-col gap-3">
        {stories.map((story, index) => (
          <Card key={story.id} className="flex items-start gap-3 p-4">
            <span className="grid size-7 shrink-0 place-items-center rounded-full bg-brand-50 text-xs font-bold text-brand-700">
              {toPersianDigits(index + 1)}
            </span>
            <p className="min-w-0 flex-1 whitespace-pre-line text-sm leading-8 text-ink-800">
              {story.content}
            </p>
            <Button
              variant="ghost"
              size="sm"
              aria-label="کپی متن استوری"
              className="size-11 shrink-0 p-0 sm:size-9"
              onClick={() => {
                void copy(story.content, "متن استوری کپی شد");
                track("caption_copied", { copy_type: "story" });
              }}
            >
              <CopyIcon width={17} height={17} />
            </Button>
          </Card>
        ))}
      </div>
    </section>
  );
}

"use client";

import { useState } from "react";
import { api, toPersianError } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import type { RewriteIntent } from "@/lib/api/types";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Sheet } from "@/components/ui/Sheet";
import { Tabs } from "@/components/ui/Tabs";
import { CopyIcon, EditIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { useClipboard } from "@/lib/hooks/useClipboard";
import type { CampaignCopy, CopyType } from "@/types/domain";
import { SectionHeading } from "./AssetSection";
import { CAPTION_REWRITE_CHIPS, RewriteChips } from "./RewriteChips";

const CAPTION_TABS: { value: CopyType; label: string }[] = [
  { value: "caption_short", label: "کوتاه و مستقیم" },
  { value: "caption_friendly", label: "صمیمی" },
  { value: "caption_persuasive", label: "تبلیغاتی" },
];

export function CaptionsSection({
  campaignId,
  copies,
  onChanged,
}: {
  campaignId: string;
  copies: CampaignCopy[];
  onChanged: () => void;
}) {
  const { toast } = useToast();
  const copy = useClipboard();

  const [active, setActive] = useState<CopyType>("caption_short");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [rewriting, setRewriting] = useState(false);

  const current = copies.find((item) => item.copy_type === active);
  const hashtags = copies.find((item) => item.copy_type === "hashtags");

  if (!current) return null;

  async function handleSave() {
    if (!current) return;
    setSaving(true);
    try {
      await api.updateCopy(campaignId, current.id, draft);
      onChanged();
      setEditing(false);
      toast("کپشن ذخیره شد");
    } catch (caught) {
      toast(toPersianError(caught), "error");
    } finally {
      setSaving(false);
    }
  }

  async function handleRewrite(intent: RewriteIntent) {
    if (!current) return;
    setRewriting(true);
    try {
      const updated = await api.rewriteCopy(campaignId, current.id, intent);
      onChanged();
      setDraft(updated.content);
      toast("متن جدید آماده شد");
    } catch (caught) {
      toast(toPersianError(caught), "error");
    } finally {
      setRewriting(false);
    }
  }

  return (
    <section>
      <SectionHeading
        title="کپشن‌ها"
        description="سه لحن مختلف؛ هرکدوم رو خواستی کپی یا ویرایش کن."
      />

      <Tabs items={CAPTION_TABS} value={active} onChange={setActive} />

      <Card className="mt-3 p-4">
        <p className="whitespace-pre-line text-[0.95rem] leading-8 text-ink-800">
          {current.content}
        </p>

        {hashtags ? (
          <p
            dir="rtl"
            className="mt-4 border-t border-ink-100 pt-3 text-sm leading-8 text-brand-700"
          >
            {hashtags.content}
          </p>
        ) : null}

        <div className="mt-4">
          <RewriteChips
            chips={CAPTION_REWRITE_CHIPS}
            onSelect={(intent) => void handleRewrite(intent)}
            disabled={rewriting || saving}
          />
        </div>

        <div className="mt-4 flex gap-2">
          <Button
            className="flex-1"
            onClick={() => {
              const text = hashtags
                ? `${current.content}\n\n${hashtags.content}`
                : current.content;
              void copy(text, "کپشن کپی شد");
              track("caption_copied", { copy_type: current.copy_type });
            }}
            iconStart={<CopyIcon width={18} height={18} />}
          >
            کپی
          </Button>
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => {
              setDraft(current.content);
              setEditing(true);
            }}
            iconStart={<EditIcon width={18} height={18} />}
          >
            ویرایش
          </Button>
        </div>
      </Card>

      <Sheet
        open={editing}
        onClose={() => setEditing(false)}
        title="ویرایش کپشن"
        footer={
          <div className="flex gap-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => setEditing(false)}
            >
              انصراف
            </Button>
            <Button className="flex-1" loading={saving} onClick={handleSave}>
              ذخیره
            </Button>
          </div>
        }
      >
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          rows={12}
          className="w-full resize-none rounded-2xl border border-ink-200 bg-white p-4 text-[0.95rem] leading-8 text-ink-900 focus:border-brand-400 focus:outline-none focus:ring-4 focus:ring-brand-100"
        />
      </Sheet>
    </section>
  );
}

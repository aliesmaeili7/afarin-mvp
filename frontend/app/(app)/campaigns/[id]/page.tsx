import type { Metadata } from "next";
import { CampaignView } from "@/features/campaign/CampaignView";

export const metadata: Metadata = { title: "کمپین من" };

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <CampaignView campaignId={id} />;
}

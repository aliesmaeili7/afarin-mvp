import { TextEditorPage } from "@/features/campaign/text-editor/TextEditorPage";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.editText");

export default async function Page({
  params,
}: {
  params: Promise<{ id: string; assetId: string }>;
}) {
  const { id, assetId } = await params;
  return <TextEditorPage campaignId={id} assetId={assetId} />;
}

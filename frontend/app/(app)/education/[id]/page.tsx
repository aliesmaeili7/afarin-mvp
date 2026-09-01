import { EducationPostView } from "@/features/education/EducationPostView";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.educationPost");

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <EducationPostView postId={id} />;
}

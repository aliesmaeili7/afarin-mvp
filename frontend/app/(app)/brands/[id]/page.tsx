import type { Metadata } from "next";
import { BrandPage } from "@/features/brand/BrandPage";

export const metadata: Metadata = { title: "هویت برند" };

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <BrandPage brandId={id} />;
}

import { redirect } from "next/navigation";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.wizardPhoto");

export default function Page() {
  redirect("/create");
}

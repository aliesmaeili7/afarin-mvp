import { redirect } from "next/navigation";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.wizardBrief");

export default function Page() {
  redirect("/create/brief");
}

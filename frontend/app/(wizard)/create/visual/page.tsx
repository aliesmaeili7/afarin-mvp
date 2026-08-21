import { redirect } from "next/navigation";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.wizardDirections");

export default function Page() {
  redirect("/create/directions");
}

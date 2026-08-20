import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.dashboard");

export default function Page() {
  return <DashboardPage />;
}

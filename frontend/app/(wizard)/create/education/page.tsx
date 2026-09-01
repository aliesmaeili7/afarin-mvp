import { EducationCreatePage } from "@/features/education/EducationCreatePage";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.educationCreate");

export default function Page() {
  return <EducationCreatePage />;
}

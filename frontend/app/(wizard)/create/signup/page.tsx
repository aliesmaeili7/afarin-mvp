import type { Metadata } from "next";
import { SignupGate } from "@/features/auth/SignupGate";

export const metadata: Metadata = { title: "ساخت حساب رایگان" };

export default function Page() {
  return <SignupGate />;
}

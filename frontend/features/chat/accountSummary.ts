import type { Session } from "@/types/domain";

export interface AccountSummary {
  signedIn: boolean;
  displayName: string | null;
  email: string | null;
  remainingCampaigns: number | null;
}

export function accountSummaryFromSession(
  session: Session | null,
): AccountSummary {
  if (!session) {
    return {
      signedIn: false,
      displayName: null,
      email: null,
      remainingCampaigns: null,
    };
  }

  const displayName = session.user.display_name.trim() || session.user.email;
  return {
    signedIn: true,
    displayName,
    email: session.user.email,
    remainingCampaigns: session.user.free_campaigns_remaining,
  };
}

export function accountInitials(name: string | null): string {
  if (!name) return "";
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0].slice(0, 2);
  return `${parts[0].slice(0, 1)}${parts[1].slice(0, 1)}`;
}

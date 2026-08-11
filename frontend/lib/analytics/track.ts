/**
 * Product analytics (spec §26).
 *
 * Phase 1 intentionally has no destination: this is a typed no-op so the call
 * sites exist with the right event names and Phase 8 only has to implement the
 * transport. Nothing here affects behaviour.
 */
export type AnalyticsEvent =
  | "landing_viewed"
  | "campaign_started"
  | "photo_uploaded"
  | "brief_completed"
  | "style_selected"
  | "concepts_generated"
  | "concept_selected"
  | "signup_started"
  | "signup_completed"
  | "generation_started"
  | "campaign_completed"
  | "asset_downloaded"
  | "caption_copied"
  | "campaign_repeated"
  | "regeneration_requested"
  | "brand_saved";

export function track(
  event: AnalyticsEvent,
  properties: Record<string, unknown> = {},
): void {
  if (process.env.NODE_ENV === "development") {
    console.debug("[analytics]", event, properties);
  }
}

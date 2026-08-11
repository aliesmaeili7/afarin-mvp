"use client";

import type { CSSProperties, Ref } from "react";
import type { AssetRenderSpec } from "@/types/domain";
import { getBackground } from "@/lib/content/backgrounds";
import { cn } from "@/components/ui/cn";
import { BackgroundLayer } from "./BackgroundLayer";
import { getTemplate } from "./templates";
import { useResolvedAssetUrl } from "./useResolvedAssetUrl";

export interface AdCanvasProps {
  spec: AssetRenderSpec;
  width: number;
  height: number;
  /** Set once the backend renders assets server-side; the image then wins. */
  storagePath?: string | null;
  className?: string;
  innerRef?: Ref<HTMLDivElement>;
}

/**
 * Composes one campaign asset in the browser.
 *
 * The background never contains text: the Persian headline, price, CTA and
 * brand name are always our own layers, which is what keeps the typography,
 * RTL layout and نیم‌فاصله correct (spec §5.6).
 */
export function AdCanvas({
  spec,
  width,
  height,
  storagePath,
  className,
  innerRef,
}: AdCanvasProps) {
  const template = getTemplate(spec.template_id);
  const background = getBackground(spec.background_id);
  const productUrl = useResolvedAssetUrl(spec.product_image_path);
  const renderedUrl = useResolvedAssetUrl(storagePath ?? null);

  const containerStyle: CSSProperties = {
    aspectRatio: `${width} / ${height}`,
    containerType: "size",
    backgroundColor: "#0f0b16",
  };

  if (renderedUrl) {
    return (
      <div
        ref={innerRef}
        dir="rtl"
        style={containerStyle}
        className={cn("relative w-full overflow-hidden", className)}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={renderedUrl}
          alt={spec.headline_fa}
          className="absolute inset-0 h-full w-full object-cover"
        />
      </div>
    );
  }

  const unit = (value: number) => `${value}cqw`;

  const productBlock = template.show_product ? (
    <div
      className="relative flex min-h-0 items-center justify-center"
      style={{ flex: template.product_flex }}
    >
      <div
        className="absolute rounded-[50%]"
        style={{
          width: "70%",
          height: "14%",
          bottom: "4%",
          background: background.stage_color,
          filter: "blur(4px)",
        }}
      />
      {productUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={productUrl}
          alt=""
          className="relative h-full w-full object-contain"
          style={{ filter: "drop-shadow(0 12px 24px rgba(0,0,0,0.35))" }}
        />
      ) : (
        <div
          className="relative rounded-[8%] border border-dashed"
          style={{
            width: "62%",
            height: "72%",
            borderColor: background.muted_text_color,
            opacity: 0.5,
          }}
        />
      )}
    </div>
  ) : null;

  const textBlock = (
    <div
      className="flex shrink-0 flex-col"
      style={{
        gap: unit(1.6),
        textAlign: template.align === "center" ? "center" : "start",
        alignItems: template.align === "center" ? "center" : "flex-start",
      }}
    >
      {/* Not a heading element: this text belongs to the artwork, not to the
          page's document outline. */}
      <div
        style={{
          fontSize: unit(template.headline_size),
          lineHeight: 1.45,
          fontWeight: 800,
          color: background.text_color,
          textWrap: "balance",
          textShadow: "0 2px 12px rgba(0,0,0,0.18)",
          margin: 0,
        }}
      >
        {spec.headline_fa}
      </div>

      {spec.subheadline_fa ? (
        <div
          style={{
            fontSize: unit(template.subheadline_size),
            lineHeight: 1.7,
            color: background.muted_text_color,
            margin: 0,
            maxWidth: "92%",
          }}
        >
          {spec.subheadline_fa}
        </div>
      ) : null}

      {template.show_cta && spec.cta_fa ? (
        <span
          style={{
            marginTop: unit(1.4),
            display: "inline-block",
            background: background.cta_bg,
            color: background.cta_text,
            fontSize: unit(template.cta_size),
            fontWeight: 700,
            borderRadius: "999px",
            paddingInline: unit(5),
            paddingBlock: unit(2.2),
            lineHeight: 1.6,
          }}
        >
          {spec.cta_fa}
        </span>
      ) : null}
    </div>
  );

  return (
    <div
      ref={innerRef}
      dir="rtl"
      style={containerStyle}
      className={cn("relative w-full overflow-hidden", className)}
    >
      <BackgroundLayer background={background} />

      <div
        className="absolute inset-0 flex flex-col"
        style={{ padding: unit(template.padding), gap: unit(3) }}
      >
        <div
          className="flex shrink-0 items-center justify-between"
          style={{ gap: unit(2), fontSize: unit(template.meta_size) }}
        >
          <span
            style={{
              color: background.text_color,
              fontWeight: 700,
              letterSpacing: "0.01em",
              opacity: spec.brand_name ? 1 : 0,
            }}
          >
            {spec.brand_name ?? "—"}
          </span>

          <span className="flex items-center" style={{ gap: unit(1.5) }}>
            {spec.slide_label_fa ? (
              <span
                style={{
                  color: background.muted_text_color,
                  border: `1px solid ${background.muted_text_color}`,
                  borderRadius: "999px",
                  paddingInline: unit(2.2),
                  paddingBlock: unit(0.6),
                  fontWeight: 600,
                }}
              >
                {spec.slide_label_fa}
              </span>
            ) : null}

            {spec.price_text ? (
              <span
                style={{
                  background: background.accent_color,
                  color: background.cta_text,
                  fontWeight: 700,
                  borderRadius: "999px",
                  paddingInline: unit(3),
                  paddingBlock: unit(1.2),
                }}
              >
                {spec.price_text}
              </span>
            ) : null}
          </span>
        </div>

        {template.order === "headline_first" ? (
          <>
            {textBlock}
            {productBlock}
          </>
        ) : template.order === "statement" ? (
          <>
            {productBlock}
            <div className="flex flex-1 items-center justify-center">{textBlock}</div>
          </>
        ) : (
          <>
            {productBlock}
            {textBlock}
          </>
        )}
      </div>
    </div>
  );
}

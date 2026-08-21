"use client";

import { catalogDescription, catalogLabel } from "@/lib/i18n/catalog";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { Locale } from "@/lib/i18n/types";
import type { VisualCatalog, VisualCatalogEntry } from "@/types/domain";
import { ChoiceCard } from "@/components/ui/ChoiceCard";
import { Skeleton } from "@/components/ui/Feedback";

export function CatalogPicker({
  locale,
  catalog,
  styleId,
  templateId,
  onStyle,
  onTemplate,
}: {
  locale: Locale;
  catalog: VisualCatalog | null;
  styleId: string | null;
  templateId: string | null;
  onStyle: (id: string) => void;
  onTemplate: (id: string) => void;
}) {
  const { t } = useI18n();
  if (!catalog) return <Skeleton className="h-40 w-full" />;
  return (
    <div className="flex flex-col gap-5">
      <section>
        <h2 className="mb-2 text-sm font-bold text-ink-700">{t("wizard.styleSection")}</h2>
        <div className="grid grid-cols-2 gap-2">
          {catalog.styles.map((item) => (
            <CatalogCard
              key={item.id}
              locale={locale}
              kind="styles"
              item={item}
              selected={styleId === item.id}
              onSelect={() => onStyle(item.id)}
            />
          ))}
        </div>
      </section>
      <section>
        <h2 className="mb-2 text-sm font-bold text-ink-700">
          {t("wizard.templateSection")}
        </h2>
        <div className="grid grid-cols-2 gap-2">
          {catalog.templates.map((item) => (
            <CatalogCard
              key={item.id}
              locale={locale}
              kind="templates"
              item={item}
              selected={templateId === item.id}
              onSelect={() => onTemplate(item.id)}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

export function PreviewPair({
  style,
  template,
}: {
  style: VisualCatalogEntry | undefined;
  template: VisualCatalogEntry | undefined;
}) {
  return (
    <div className="grid grid-cols-2 gap-px bg-ink-100">
      {style ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={style.preview_path} alt="" className="aspect-4/5 w-full object-cover" />
      ) : null}
      {template ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={template.preview_path}
          alt=""
          className="aspect-4/5 w-full object-cover"
        />
      ) : null}
    </div>
  );
}

function CatalogCard({
  locale,
  kind,
  item,
  selected,
  onSelect,
}: {
  locale: Locale;
  kind: "styles" | "templates";
  item: VisualCatalogEntry;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <ChoiceCard
      selected={selected}
      onSelect={onSelect}
      title={catalogLabel(locale, kind, item.id, item.label_fa)}
      description={catalogDescription(locale, kind, item.id, item.description_fa)}
      media={
        // eslint-disable-next-line @next/next/no-img-element
        <img src={item.preview_path} alt="" className="aspect-4/5 w-full object-cover" />
      }
    />
  );
}

export function entryOf(
  catalog: VisualCatalog | null,
  kind: "styles" | "templates",
  id: string,
) {
  return catalog?.[kind].find((item) => item.id === id);
}

"""Pre-run cost and call plan. Counts paid image frames, not HTTP requests."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

ESTIMATED_IMAGE_USD = Decimal("0.04")


@dataclass
class EvalPlan:
    case_id: str
    mode: str
    recipes: list[dict[str, str]]
    candidates: int
    quality_check: bool
    repair: str
    story: bool
    master_crop: bool
    provider: str
    paid: bool
    label: str | None = None
    experiment_id: str | None = None
    concurrency: int = 2
    director_llm_calls: int = 0
    architect_llm_calls: int = 0
    qc_llm_calls: int = 0
    image_candidates: int = 0
    image_repairs_max: int = 0
    image_story: int = 0
    image_master: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def image_outputs(self) -> int:
        return (
            self.image_candidates
            + self.image_story
            + self.image_master
        )

    @property
    def estimated_image_usd(self) -> Decimal:
        extra = self.image_repairs_max if self.repair == "production" else 0
        return ESTIMATED_IMAGE_USD * (self.image_outputs + extra)

    @property
    def sweep(self) -> bool:
        return len(self.recipes) > 3 and self.mode == "fixed"


def build_plan(
    *,
    case_id: str,
    mode: str,
    recipes: list[dict[str, str]],
    candidates: int,
    quality_check: bool,
    repair: str,
    story: bool,
    master_crop: bool,
    provider: str,
    paid: bool,
    label: str | None,
    concurrency: int = 2,
    experiment_id: str | None = None,
) -> EvalPlan:
    count = len(recipes)
    story_on = story or master_crop
    plan = EvalPlan(
        case_id=case_id,
        mode=mode,
        recipes=recipes,
        candidates=candidates,
        quality_check=quality_check,
        repair=repair,
        story=story_on,
        master_crop=master_crop,
        provider=provider,
        paid=paid,
        label=label,
        experiment_id=experiment_id,
        concurrency=max(1, min(3, concurrency)),
        director_llm_calls=1 if mode == "director" else 0,
        architect_llm_calls=count if candidates > 0 else 0,
        qc_llm_calls=count if quality_check and candidates > 0 else 0,
        image_candidates=count * max(0, candidates),
        image_repairs_max=(
            count if repair == "production" and candidates > 0 else 0
        ),
        image_story=count if story_on and candidates > 0 else 0,
        image_master=count if master_crop and candidates > 0 else 0,
    )
    if repair == "production":
        plan.notes.append(
            "repair=production may add at most one extra image per recipe"
        )
    if quality_check and repair == "production":
        plan.qc_llm_calls += count
        plan.notes.append("QC may run a second time on a repair frame")
    if mode == "fixed":
        plan.notes.append("Creative Director will not be called")
    else:
        plan.notes.append("Creative Director will be called exactly once")
    return plan


def render_plan(plan: EvalPlan) -> str:
    recipe_lines = [
        f"  - {item['style_id']} × {item['template_id']}"
        for item in plan.recipes
    ] or ["  (none yet — Director will propose 3)"]
    repair_note = (
        f"{plan.image_repairs_max} max (only if QC hard-fails)"
        if plan.image_repairs_max
        else "0"
    )
    lines = [
        "Creative eval plan",
        f"  case:            {plan.case_id}",
        f"  mode:            {plan.mode}",
        f"  label:           {plan.label or '—'}",
        f"  provider:        {plan.provider}",
        f"  paid:            {plan.paid}",
        f"  quality-check:   {plan.quality_check}",
        f"  repair:          {plan.repair}",
        f"  story:           {plan.story}",
        f"  master-crop:     {plan.master_crop}",
        f"  concurrency:     {plan.concurrency}",
        "  recipes:",
        *recipe_lines,
        "  LLM calls:",
        f"    Director:      {plan.director_llm_calls}",
        f"    Architect:     {plan.architect_llm_calls}",
        f"    QC:            {plan.qc_llm_calls}",
        "  Image outputs (paid frames, not HTTP requests):",
        f"    Candidates:    {plan.image_candidates}",
        f"    Repairs:       {repair_note}",
        f"    Story:         {plan.image_story}",
        f"    Master 9:16:   {plan.image_master}",
        f"    Total (excl. optional repairs): {plan.image_outputs}",
        f"  Approx. image cost: ${plan.estimated_image_usd} "
        f"(${ESTIMATED_IMAGE_USD}/frame estimate; actual recorded after run)",
    ]
    for note in plan.notes:
        lines.append(f"  note: {note}")
    return "\n".join(lines)

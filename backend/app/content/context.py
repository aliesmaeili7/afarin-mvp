from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PreviousConcept:
    """A concept the seller already saw, so regeneration cannot paraphrase it."""

    title_fa: str
    description_fa: str
    visual_direction: str


@dataclass(frozen=True, slots=True)
class CopyContext:
    """
    Everything the content provider needs to produce copy that actually mentions
    the seller's product. Assembled from the campaign brief so different answers
    visibly produce different Persian output.
    """

    product_name: str
    description: str | None
    price_text: str | None
    benefit: str | None
    brand_name: str | None
    audience: str | None
    objective: str
    style: str
    # Increments each time the seller asks for fresh output.
    round: int
    selected_headline: str | None = None
    selected_angle: str | None = None
    selected_description: str | None = None
    previous_concepts: tuple[PreviousConcept, ...] = ()


def pick[T](items: tuple[T, ...] | list[T], index: int) -> T:
    return items[((index % len(items)) + len(items)) % len(items)]


def rotate[T](items: tuple[T, ...] | list[T], offset: int) -> list[T]:
    """Rotates a list so repeat requests return a different order."""
    if not items:
        return []
    shift = ((offset % len(items)) + len(items)) % len(items)
    return [*items[shift:], *items[:shift]]

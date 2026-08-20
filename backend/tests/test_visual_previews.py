"""One-time preview asset script. Never called from campaign requests."""

import io
from pathlib import Path

from PIL import Image

from app.content.visual_catalog import public_catalog, styles, templates
from app.providers.image.base import ImageRequest
from app.providers.image.stub import StubImageProvider
from scripts.generate_visual_previews import (
    DEMO_PRODUCT,
    IDENTITY,
    STYLE_COMPOSITION,
    TEMPLATE_STYLE,
    build_style_prompt,
    build_template_prompt,
    generate_all,
    load_reference,
    main,
    preview_jobs,
    to_preview_jpeg,
    write_catalog,
    write_placeholders,
)

FORBIDDEN = (
    "nike",
    "adidas",
    "gucci",
    "disney",
    "marvel",
    "ghibli",
    "miyazaki",
    "wes anderson",
    "kubrick",
    "tarantino",
    "star wars",
    "pixar",
    "nintendo",
    "pokemon",
    "akira",
    "midjourney",
    "in the style of",
)


def test_demo_product_exists() -> None:
    assert DEMO_PRODUCT.is_file()
    image = Image.open(DEMO_PRODUCT)
    assert min(image.size) >= 256


def test_style_prompts_share_composition_and_vary_look() -> None:
    prompts = [build_style_prompt(item) for item in styles()]
    assert len(prompts) == 14
    for prompt, item in zip(prompts, styles(), strict=True):
        lowered = prompt.lower()
        assert STYLE_COMPOSITION.split(",")[0] in prompt
        assert IDENTITY.split(":")[0] in prompt
        assert item["prompt_atoms"].split(",")[0] in prompt
        assert "no readable text" in lowered
        assert not any(term in lowered for term in FORBIDDEN)
    looks = {item["prompt_atoms"] for item in styles()}
    assert len(looks) == 14


def test_template_prompts_share_photoreal_and_vary_scene() -> None:
    photoreal = next(item for item in styles() if item["id"] == "photoreal_commercial")
    prompts = [build_template_prompt(item) for item in templates()]
    assert len(prompts) == 12
    for prompt, item in zip(prompts, templates(), strict=True):
        lowered = prompt.lower()
        assert TEMPLATE_STYLE.split(",")[0] in prompt
        assert photoreal["prompt_atoms"].split(",")[0] in prompt
        assert item["prompt_atoms"].split(",")[0] in prompt
        assert "no readable text" in lowered
        assert not any(term in lowered for term in FORBIDDEN)
    scenes = {item["prompt_atoms"] for item in templates()}
    assert len(scenes) == 12


def test_preview_jobs_cover_both_libraries() -> None:
    jobs = preview_jobs()
    assert [job.item_id for job in jobs if job.kind == "styles"] == [
        item["id"] for item in styles()
    ]
    assert [job.item_id for job in jobs if job.kind == "templates"] == [
        item["id"] for item in templates()
    ]
    subset = preview_jobs(ids={"anime", "flat_lay"})
    assert {(job.kind, job.item_id) for job in subset} == {
        ("styles", "anime"),
        ("templates", "flat_lay"),
    }


def test_catalog_and_placeholders_write_under_out_root(tmp_path: Path) -> None:
    write_placeholders(tmp_path)
    catalog = public_catalog()
    written = (tmp_path / "catalog.json").read_text(encoding="utf-8")
    assert catalog["styles"][0]["id"] in written
    assert "prompt_atoms" not in written
    anime = Image.open(tmp_path / "styles" / "anime.jpg")
    assert anime.size == (640, 800)
    assert anime.format == "JPEG"


def test_to_preview_jpeg_is_4x5() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (1200, 800), (12, 40, 80)).save(buffer, format="JPEG")
    image = Image.open(io.BytesIO(to_preview_jpeg(buffer.getvalue())))
    assert abs(image.width / image.height - 0.8) < 0.02
    assert image.width <= 1280


class _RecordingStub(StubImageProvider):
    def __init__(self) -> None:
        self.calls: list[ImageRequest] = []

    async def generate(self, request: ImageRequest):
        self.calls.append(request)
        return await super().generate(request)


async def test_stub_generation_attaches_the_demo_product(tmp_path: Path) -> None:
    provider = _RecordingStub()
    reference = load_reference()
    jobs = preview_jobs(ids={"cinematic", "hero_product"})
    failures = await generate_all(
        jobs,
        provider=provider,
        reference=reference,
        public=tmp_path,
        concurrency=2,
    )
    assert failures == []
    for job in jobs:
        path = tmp_path / job.kind / f"{job.item_id}.jpg"
        assert path.stat().st_size > 100
        assert Image.open(path).format == "JPEG"
    assert len(provider.calls) == 2
    assert all(call.references == (reference,) for call in provider.calls)
    assert all(call.aspect_ratio == "4:5" for call in provider.calls)
    assert "attached product photo" in jobs[0].prompt


def test_main_dry_run_lists_jobs(capsys) -> None:
    assert main(["--dry-run", "--only", "styles"]) == 0
    out = capsys.readouterr().out
    assert "anime" in out
    assert "hero_product" not in out


def test_main_without_live_does_not_overwrite() -> None:
    assert main([]) == 2


def test_write_catalog_matches_public_api(tmp_path: Path) -> None:
    path = write_catalog(tmp_path)
    body = path.read_text(encoding="utf-8")
    catalog = public_catalog()
    assert catalog["templates"][-1]["id"] in body
    assert all(
        item["preview_path"].startswith("/visual-previews/")
        for item in catalog["styles"]
    )

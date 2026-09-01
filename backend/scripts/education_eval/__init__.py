"""
A small smoke harness for the educational path.

Deliberately self-contained. `scripts.creative_eval` is not importable at the
moment (its `cases` module still imports `style_ids` from the visual catalog,
which the unified refactor removed), and this harness should not be able to
break for reasons unrelated to educational content. The few helpers it needs
are ~20 lines and are defined here.

Stub providers are the default, so `python -m scripts.education_eval` costs
nothing. Real calls require an explicit --live.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from adapters.llm_client import LLMClient
from domain.models import CatalogStatus, Measure, MeasureCatalog, MeasureCategory, Synthesis


@dataclass(frozen=True)
class _MeasureSpec:
    title: str
    category: MeasureCategory
    impact: int
    effort: int
    description_template: str
    measure_class: str
    prerequisites: list[str]
    dependencies: list[str]


class RecommendationService:
    def __init__(
        self,
        config_path: Path | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._llm_client = llm_client or LLMClient(dry_run=True)
        self._config_path = config_path or Path("app/config/recommendation_catalog_v1.0.json")
        self._config = self._load_config()

    def generate_catalog(
        self,
        synthesis: Synthesis,
        bi_maturity_label: str,
        pa_maturity_label: str,
        bi_dimension_scores: dict[str, float],
        pa_dimension_scores: dict[str, float],
        bi_dimension_levels: dict[str, str] | None = None,
        pa_dimension_levels: dict[str, str] | None = None,
        use_llm_texts: bool = False,
    ) -> MeasureCatalog:
        level_by_dimension = {**(bi_dimension_levels or {}), **(pa_dimension_levels or {})}
        scores = {**bi_dimension_scores, **pa_dimension_scores}

        if not level_by_dimension:
            level_by_dimension = {
                dimension: (bi_maturity_label if dimension.startswith("BI_") else pa_maturity_label)
                for dimension in scores
            }

        specs: list[tuple[str, str, float, _MeasureSpec]] = []
        for dimension, level in level_by_dimension.items():
            score = scores.get(dimension, 0.0)
            spec = self._resolve_spec_for_dimension(dimension, level)
            if spec:
                specs.append((dimension, level, score, spec))

        if not specs:
            fallback = self._resolve_fallback_spec()
            if fallback:
                specs.append(("GLOBAL", "N/A", 0.0, fallback))

        factors = synthesis.context_factors or {"GLOBAL": 1.0}

        ranked_specs = sorted(
            specs,
            key=lambda item: (100 - item[2]) * factors.get(item[0], factors.get("GLOBAL", 1.0)),
            reverse=True,
        )

        llm_texts: list[str] = []
        if use_llm_texts:
            llm_texts = self._llm_client.draft_measures([spec.title for _, _, _, spec in ranked_specs], max_measures=len(ranked_specs))

        measures: list[Measure] = []
        for index, (dimension, level, score, spec) in enumerate(ranked_specs, start=1):
            priority_score = round((100 - score) * factors.get(dimension, factors.get("GLOBAL", 1.0)), 2)
            llm_suffix = ""
            if index - 1 < len(llm_texts):
                llm_suffix = f" LLM-Hinweis: {llm_texts[index - 1]}"

            description = (
                f"{spec.description_template} "
                f"Bezug: {synthesis.priority_focus}. "
                f"Heuristik: {synthesis.heuristic_reason}."
                f"{llm_suffix}"
            )
            measures.append(
                Measure(
                    measure_id=f"mea-{uuid4().hex[:12]}",
                    title=spec.title,
                    description=description.strip(),
                    category=spec.category,
                    dimension=dimension,
                    maturity_label=level,
                    measure_class=spec.measure_class,
                    impact=spec.impact,
                    effort=spec.effort,
                    priority_score=priority_score,
                    prerequisites=spec.prerequisites,
                    dependencies=spec.dependencies,
                    suggested_priority=index,
                )
            )

        return MeasureCatalog(
            catalog_id=f"cat-{uuid4().hex[:12]}",
            title=f"Maßnahmenkatalog für {synthesis.answer_set_id}",
            status=CatalogStatus.DRAFT,
            synthesis_id=synthesis.synthesis_id,
            measures=measures,
        )

    def _resolve_spec_for_dimension(self, dimension: str, level: str) -> _MeasureSpec | None:
        entry = self._config.get("dimension_level_mapping", {}).get(dimension, {}).get(level)
        if not entry:
            return None
        return self._to_spec(entry)

    def _resolve_fallback_spec(self) -> _MeasureSpec | None:
        entry = self._config.get("fallback")
        if not entry:
            return None
        return self._to_spec(entry)

    def _load_config(self) -> dict:
        with self._config_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _to_spec(entry: dict) -> _MeasureSpec:
        return _MeasureSpec(
            title=str(entry["title"]),
            category=MeasureCategory(str(entry["category"])),
            impact=int(entry.get("impact", 1)),
            effort=int(entry.get("effort", 1)),
            description_template=str(entry.get("description_template", "")),
            measure_class=str(entry.get("measure_class", "Fundament schaffen")),
            prerequisites=[str(x) for x in entry.get("prerequisites", [])],
            dependencies=[str(x) for x in entry.get("dependencies", [])],
        )

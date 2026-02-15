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
    dimension: str
    maturity_label: str


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
        use_llm_texts: bool = False,
    ) -> MeasureCatalog:
        weakest_dimensions = [
            self._lowest_dimension(bi_dimension_scores),
            self._lowest_dimension(pa_dimension_scores),
        ]

        specs: list[_MeasureSpec] = []
        for dimension in weakest_dimensions:
            level = bi_maturity_label if dimension.startswith("BI_") else pa_maturity_label
            specs.extend(self._resolve_specs_for_dimension(dimension, level))

        if not specs:
            specs.extend(self._resolve_fallback_specs())

        prioritized = sorted(specs, key=lambda item: (item.impact * 2 - item.effort, item.impact), reverse=True)

        llm_texts: list[str] = []
        if use_llm_texts:
            llm_texts = self._llm_client.draft_measures([spec.title for spec in prioritized], max_measures=len(prioritized))

        measures: list[Measure] = []
        for index, spec in enumerate(prioritized, start=1):
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
                    dimension=spec.dimension,
                    maturity_label=spec.maturity_label,
                    impact=spec.impact,
                    effort=spec.effort,
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

    def _resolve_specs_for_dimension(self, dimension: str, level: str) -> list[_MeasureSpec]:
        dimension_mapping = self._config.get("dimension_level_mapping", {}).get(dimension, {})
        entries = dimension_mapping.get(level, [])
        return [self._to_spec(entry, dimension, level) for entry in entries]

    def _resolve_fallback_specs(self) -> list[_MeasureSpec]:
        entries = self._config.get("fallback", [])
        return [self._to_spec(entry, "GLOBAL", "N/A") for entry in entries]

    @staticmethod
    def _lowest_dimension(dimension_scores: dict[str, float]) -> str:
        if not dimension_scores:
            return "GLOBAL"
        return min(dimension_scores.items(), key=lambda item: item[1])[0]

    def _load_config(self) -> dict:
        with self._config_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _to_spec(entry: dict, dimension: str, maturity_label: str) -> _MeasureSpec:
        return _MeasureSpec(
            title=str(entry["title"]),
            category=MeasureCategory(str(entry["category"])),
            impact=int(entry.get("impact", 1)),
            effort=int(entry.get("effort", 1)),
            description_template=str(entry.get("description_template", "")),
            dimension=dimension,
            maturity_label=maturity_label,
        )

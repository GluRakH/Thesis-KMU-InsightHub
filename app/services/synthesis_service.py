from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from adapters.llm_client import LLMClient
from domain.models import BIAssessment, PAAssessment, Synthesis


@dataclass(frozen=True)
class SynthesisHeuristicResult:
    priority_focus: str
    reason: str


class SynthesisService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm_client = llm_client or LLMClient()

    def synthesize(self, bi_assessment: BIAssessment, pa_assessment: PAAssessment) -> Synthesis:
        heuristic = self._resolve_dependency_heuristic(bi_assessment, pa_assessment)
        combined_summary = self._build_combined_summary(bi_assessment, pa_assessment)

        llm_summary = self._llm_client.summarize_use_case(
            company_context=(
                "Synthesis aus BI- und PA-Assessment. "
                f"BI-Score: {bi_assessment.score:.2f}, PA-Score: {pa_assessment.score:.2f}."
            ),
            bi_findings={
                "summary": bi_assessment.summary,
                "dimension_scores": bi_assessment.dimension_scores,
                "findings": bi_assessment.findings,
            },
            pa_findings={
                "summary": pa_assessment.summary,
                "dimension_scores": pa_assessment.dimension_scores,
                "findings": pa_assessment.findings,
            },
        )

        recommendation = (
            f"{heuristic.priority_focus}. {heuristic.reason} "
            "Nutze 90-Tage-Meilensteine und überprüfe monatlich die KPI-Wirkung."
        )

        return Synthesis(
            synthesis_id=f"syn-{uuid4().hex[:12]}",
            answer_set_id=bi_assessment.answer_set_id,
            bi_assessment_id=bi_assessment.bi_assessment_id,
            pa_assessment_id=pa_assessment.pa_assessment_id,
            combined_summary=f"{combined_summary} {llm_summary}".strip(),
            priority_focus=heuristic.priority_focus,
            heuristic_reason=heuristic.reason,
            questionnaire_version=bi_assessment.questionnaire_version,
            scoring_version=bi_assessment.scoring_version,
            llm_model=self._llm_client.config.model,
            llm_prompt_version=self._llm_client.config.prompt_version,
            model_version="synthesis-rules-v1",
            prompt_version=self._llm_client.config.prompt_version,
            recommendation=recommendation,
        )

    @staticmethod
    def _build_combined_summary(bi_assessment: BIAssessment, pa_assessment: PAAssessment) -> str:
        weakest_bi = SynthesisService._lowest_dimension(bi_assessment.dimension_scores)
        weakest_pa = SynthesisService._lowest_dimension(pa_assessment.dimension_scores)
        return (
            f"BI steht bei Reifegrad {bi_assessment.maturity_level} ({bi_assessment.level_label}) "
            f"mit Score {bi_assessment.score:.2f}; kritischste BI-Dimension: {weakest_bi}. "
            f"PA steht bei Reifegrad {pa_assessment.maturity_level} ({pa_assessment.level_label}) "
            f"mit Score {pa_assessment.score:.2f}; kritischste PA-Dimension: {weakest_pa}."
        )

    @staticmethod
    def _resolve_dependency_heuristic(
        bi_assessment: BIAssessment,
        pa_assessment: PAAssessment,
    ) -> SynthesisHeuristicResult:
        if bi_assessment.score <= 2.0 and pa_assessment.score >= 3.0:
            return SynthesisHeuristicResult(
                priority_focus="Fokus zuerst auf Datenfundament und KPI-Steuerung",
                reason=(
                    "PA-Bereitschaft ist höher als BI-Reife; ohne konsistente Daten und KPI-Definitionen "
                    "wird Automatisierung instabil und schwer messbar"
                ),
            )

        if pa_assessment.score <= 2.0 and bi_assessment.score >= 3.0:
            return SynthesisHeuristicResult(
                priority_focus="Fokus zuerst auf Prozessstandardisierung und Automatisierungsfähigkeit",
                reason=(
                    "BI-Erkenntnisse sind vorhanden, aber PA-Reife ist zu niedrig; "
                    "ohne standardisierte Prozesse fehlt die Grundlage für skalierbare Automatisierung"
                ),
            )

        return SynthesisHeuristicResult(
            priority_focus="Parallelisierung mit ausgewogenem BI/PA-Backlog",
            reason=(
                "BI- und PA-Reife sind ähnlich; ein abgestimmtes Maßnahmenpaket reduziert Risiken "
                "und verbessert Time-to-Value"
            ),
        )

    @staticmethod
    def _lowest_dimension(dimension_scores: dict[str, float]) -> str:
        if not dimension_scores:
            return "keine Daten"
        return min(dimension_scores.items(), key=lambda item: item[1])[0]

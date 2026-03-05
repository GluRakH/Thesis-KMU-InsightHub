from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import streamlit as st
from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from adapters.llm_client import LLMClient
from app.services.assessment_service import AssessmentService
from app.services.export_service import build_export_payload, payload_to_json, payload_to_markdown
from app.services.questionnaire_service import QuestionType, QuestionnaireService
from app.services.recommendation_service import RecommendationService
from app.services.synthesis_service import SynthesisService
from domain.models import Answer, AnswerSet, AnswerSetStatus, Synthesis, UseCase, UseCaseType, UserSelection
from persistence.database import Base, create_sqlite_engine, create_session_factory
from persistence.entities import (
    AnswerSetEntity,
    BIAssessmentEntity,
    MeasureCatalogEntity,
    PAAssessmentEntity,
    SynthesisEntity,
    UseCaseEntity,
)
from persistence.repositories import PersistenceRepository, load_catalog


@dataclass
class PipelineResult:
    bi: dict
    pa: dict
    synthesis: dict


st.set_page_config(page_title="InsightHub", layout="wide")

engine = create_sqlite_engine()
Base.metadata.create_all(engine)
session_factory = create_session_factory()

questionnaire_service = QuestionnaireService()
assessment_service = AssessmentService()

STEP_ORDER = ["Start", "Fragebogen", "Ergebnisse", "Maßnahmen", "Export"]
STEP_LABELS = {
    "Start": "1. Start",
    "Fragebogen": "2. Fragebogen",
    "Ergebnisse": "3. Ergebnisse",
    "Maßnahmen": "4. Maßnahmen",
    "Export": "5. Export",
}


def _init_state() -> None:
    defaults = {
        "use_case_id": None,
        "answer_set_id": None,
        "catalog_id": None,
        "version": "v1.0",
        "answers": {},
        "validation": None,
        "pipeline": None,
        "export_version": "1.1.0",
        "active_step": "Start",
        "use_llm_texts": True,
        "catalog_summary": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _build_llm_client() -> LLMClient:
    return LLMClient(dry_run=False)


def _render_multi_choice_checkboxes(
    question_id: str,
    label: str,
    options: list[object],
    current_value: object,
) -> list[str]:
    st.markdown(f"**{label}**")
    if not options:
        return []

    selected: list[str] = []
    default_values = current_value if isinstance(current_value, list) else []
    columns = st.columns(min(3, max(1, len(options))))
    for idx, option in enumerate(options):
        key = f"q_{question_id}_opt_{idx}"
        with columns[idx % len(columns)]:
            checked = st.checkbox(str(option), value=str(option) in [str(x) for x in default_values], key=key)
        if checked:
            selected.append(str(option))
    return selected


def _render_single_choice(
    question_id: str,
    label: str,
    options: list[object],
    current_value: object,
) -> object:
    if not options:
        return None

    normalized_options = [str(option) for option in options]
    default_index = normalized_options.index(str(current_value)) if str(current_value) in normalized_options else None

    return st.radio(
        label,
        options=normalized_options,
        index=default_index,
        horizontal=True,
        key=f"q_{question_id}",
    )


def _render_question(question: dict, current_value: object) -> object:
    question_id = question["id"]
    label = question["text"]
    q_type = QuestionType(question["type"])

    if q_type == QuestionType.TEXT:
        return st.text_area(label, value=current_value or "", key=f"q_{question_id}")

    if q_type == QuestionType.SINGLE_CHOICE:
        return _render_single_choice(question_id, label, question.get("options", []), current_value)

    if q_type == QuestionType.MULTI_CHOICE:
        return _render_multi_choice_checkboxes(question_id, label, question.get("options", []), current_value)

    if q_type == QuestionType.NUMBER:
        default_value = float(current_value) if isinstance(current_value, (int, float)) else 0.0
        return st.number_input(label, value=default_value, key=f"q_{question_id}")

    if q_type == QuestionType.SCALE:
        scale = question.get("scale") or {"min": 1, "max": 5}
        min_value = int(scale.get("min", 1))
        max_value = int(scale.get("max", 5))
        options = list(range(min_value, max_value + 1))
        selected = _render_single_choice(question_id, label, options, current_value)
        return None if selected is None else int(selected)

    raise ValueError(f"Unbekannter Fragetyp: {q_type}")


def _persist_answers(use_case_id: str, answer_set_id: str, version: str, answers: dict, lock: bool = False) -> None:
    status = AnswerSetStatus.LOCKED if lock else AnswerSetStatus.SUBMITTED
    with session_factory() as session:
        repository = PersistenceRepository(session)
        repository.save_answer_set(
            AnswerSet(
                answer_set_id=answer_set_id,
                questionnaire_id=use_case_id,
                status=status,
                prompt_version=f"questionnaire_{version}",
            ),
            [
                Answer(
                    answer_id=f"ans-{uuid4().hex[:12]}",
                    answer_set_id=answer_set_id,
                    question_id=question_id,
                    value=json.dumps(value, ensure_ascii=False),
                )
                for question_id, value in answers.items()
            ],
        )


def _load_answers(answer_set_id: str) -> dict[str, object]:
    with session_factory() as session:
        loaded = PersistenceRepository(session).load_answer_set(answer_set_id)
        if loaded is None:
            return {}
        _, answers = loaded
        return {answer.question_id: json.loads(answer.value) for answer in answers}


def _run_pipeline(answer_set_id: str, version: str) -> PipelineResult:
    answers = _load_answers(answer_set_id)
    validation = questionnaire_service.validate_answer_set(version, answers)
    if not validation.valid:
        raise ValueError("Antworten sind nicht valide. Bitte den Fragebogen prüfen.")

    bi_assessment = assessment_service.compute_bi_assessment(answer_set_id, answers, version)
    pa_assessment = assessment_service.compute_pa_assessment(answer_set_id, answers, version)
    synthesis = SynthesisService(llm_client=_build_llm_client()).synthesize(bi_assessment, pa_assessment)

    with session_factory() as session:
        repository = PersistenceRepository(session)
        repository.save_assessments(bi_assessment, pa_assessment)
        repository.save_synthesis(synthesis)

    return PipelineResult(
        bi=bi_assessment.model_dump(),
        pa=pa_assessment.model_dump(),
        synthesis=synthesis.model_dump(),
    )


def _load_latest_pipeline(answer_set_id: str) -> PipelineResult | None:
    with session_factory() as session:
        bi = session.scalar(
            select(BIAssessmentEntity)
            .where(BIAssessmentEntity.answer_set_id == answer_set_id)
            .order_by(BIAssessmentEntity.created_at.desc())
            .limit(1)
        )
        pa = session.scalar(
            select(PAAssessmentEntity)
            .where(PAAssessmentEntity.answer_set_id == answer_set_id)
            .order_by(PAAssessmentEntity.created_at.desc())
            .limit(1)
        )
        synthesis = session.scalar(
            select(SynthesisEntity)
            .where(SynthesisEntity.details["answer_set_id"].as_string() == answer_set_id)
            .order_by(SynthesisEntity.created_at.desc())
            .limit(1)
        )

    if bi is None or pa is None or synthesis is None:
        return None

    return PipelineResult(
        bi={
            "bi_assessment_id": bi.bi_assessment_id,
            "score": bi.score,
            "summary": bi.summary,
            "level_label": bi.details.get("level_label", ""),
            "maturity_level": bi.details.get("maturity_level", 0),
            "dimension_scores": bi.details.get("dimension_scores", {}),
            "findings": bi.details.get("findings", {}),
            "critical_dimension_id": bi.details.get("critical_dimension_id", ""),
            "critical_dimension_severity": bi.details.get("critical_dimension_severity", 0.0),
            "critical_dimension_top_items": bi.details.get("critical_dimension_top_items", []),
        },
        pa={
            "pa_assessment_id": pa.pa_assessment_id,
            "score": pa.score,
            "summary": pa.summary,
            "level_label": pa.details.get("level_label", ""),
            "maturity_level": pa.details.get("maturity_level", 0),
            "dimension_scores": pa.details.get("dimension_scores", {}),
            "findings": pa.details.get("findings", {}),
            "critical_dimension_id": pa.details.get("critical_dimension_id", ""),
            "critical_dimension_severity": pa.details.get("critical_dimension_severity", 0.0),
            "critical_dimension_top_items": pa.details.get("critical_dimension_top_items", []),
        },
        synthesis={
            "synthesis_id": synthesis.synthesis_id,
            "answer_set_id": synthesis.details.get("answer_set_id", ""),
            "combined_summary": synthesis.details.get("combined_summary", ""),
            "priority_focus": synthesis.details.get("priority_focus", ""),
            "heuristic_reason": synthesis.details.get("heuristic_reason", ""),
            "recommendation": synthesis.recommendation,
        },
    )


def _render_header() -> str:
    st.title("InsightHub")
    current_step = st.radio(
        "Prozessschritte",
        options=STEP_ORDER,
        index=STEP_ORDER.index(st.session_state["active_step"]),
        horizontal=True,
        format_func=lambda step: STEP_LABELS[step],
        key="step_navigation",
        label_visibility="collapsed",
    )
    st.session_state["active_step"] = current_step

    st.progress((STEP_ORDER.index(st.session_state["active_step"]) + 1) / len(STEP_ORDER))
    return st.session_state["active_step"]


def _render_start() -> None:
    st.subheader("Start: Use Case erfassen")
    with st.form("use_case_form"):
        name = st.text_input("Titel", value="")
        description = st.text_area("Beschreibung", value="")
        use_case_type = st.selectbox(
            "Typ",
            options=[UseCaseType.COMBINED, UseCaseType.BUSINESS_IMPACT, UseCaseType.PROCESS_AUTOMATION],
            format_func=lambda item: item.value,
        )
        submitted = st.form_submit_button("Use Case speichern")

    if submitted:
        if not name.strip() or not description.strip():
            st.error("Bitte Titel und Beschreibung ausfüllen.")
            return

        use_case_id = f"uc-{uuid4().hex[:12]}"
        use_case = UseCase(
            use_case_id=use_case_id,
            name=name.strip(),
            description=description.strip(),
            use_case_type=use_case_type,
        )
        with session_factory() as session:
            PersistenceRepository(session).create_use_case(use_case)

        st.session_state["use_case_id"] = use_case_id
        st.session_state["answer_set_id"] = f"as-{uuid4().hex[:12]}"
        st.success(f"Use Case gespeichert: {use_case_id}")

    if st.session_state["use_case_id"]:
        st.info(f"Aktiver Use Case: {st.session_state['use_case_id']}")


def _group_questions(questions: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for question in questions:
        prefix = str(question["id"]).split("_", maxsplit=1)[0]
        grouped.setdefault(prefix, []).append(question)
    return grouped


def _render_questionnaire() -> None:
    st.subheader("Fragebogen: beantworten, speichern und validieren")
    use_case_id = st.session_state["use_case_id"]
    if not use_case_id:
        st.warning("Bitte zuerst im Schritt Start einen Use Case anlegen.")
        return

    questionnaire = questionnaire_service.get_questionnaire(st.session_state["version"])
    question_payload = questionnaire.model_dump()["questions"]
    grouped_questions = _group_questions(question_payload)

    with st.form("questionnaire_form"):
        answers: dict[str, object] = {}
        for group_id, questions in grouped_questions.items():
            with st.expander(f"Themenblock {group_id}", expanded=True):
                for question in questions:
                    current = st.session_state["answers"].get(question["id"])
                    answers[question["id"]] = _render_question(question, current)
                    st.caption(f"Frage-ID: {question['id']}")

        save_clicked = st.form_submit_button("Antworten speichern")
        validate_clicked = st.form_submit_button("Validierung starten")

    if save_clicked:
        st.session_state["answers"] = answers
        _persist_answers(
            use_case_id=use_case_id,
            answer_set_id=st.session_state["answer_set_id"],
            version=st.session_state["version"],
            answers=answers,
            lock=False,
        )
        st.success("Antworten gespeichert.")

    if validate_clicked:
        st.session_state["answers"] = answers
        result = questionnaire_service.validate_answer_set(st.session_state["version"], answers)
        st.session_state["validation"] = result.model_dump()
        if result.valid:
            _persist_answers(
                use_case_id=use_case_id,
                answer_set_id=st.session_state["answer_set_id"],
                version=st.session_state["version"],
                answers=answers,
                lock=True,
            )
            st.success("Antworten valide und als LOCKED gespeichert.")
        else:
            st.error("Validierung fehlgeschlagen.")

    if st.session_state["validation"]:
        st.json(st.session_state["validation"])


def _render_results() -> None:
    st.subheader("Ergebnisse: BI/PA-Bewertung und Synthese")
    answer_set_id = st.session_state["answer_set_id"]
    if not answer_set_id:
        st.warning("Bitte zuerst Use Case und Antworten erfassen.")
        return

    if st.button("Bewertung und Synthese berechnen"):
        try:
            st.session_state["pipeline"] = _run_pipeline(answer_set_id, st.session_state["version"]).__dict__
            st.success("Bewertungen und Synthese wurden berechnet und gespeichert.")
        except ValueError as exc:
            st.error(str(exc))

    if st.session_state["pipeline"] is None:
        loaded = _load_latest_pipeline(answer_set_id)
        if loaded is not None:
            st.session_state["pipeline"] = loaded.__dict__

    pipeline = st.session_state["pipeline"]
    if pipeline is None:
        st.info("Noch keine Ergebnisse vorhanden.")
        return

    bi_col, pa_col = st.columns(2)
    with bi_col:
        st.markdown("### BI-Bewertung")
        st.metric("Punktzahl", f"{pipeline['bi']['score']:.2f}")
        st.write(pipeline["bi"]["summary"])
        st.json(pipeline["bi"]["dimension_scores"])

    with pa_col:
        st.markdown("### PA-Bewertung")
        st.metric("Punktzahl", f"{pipeline['pa']['score']:.2f}")
        st.write(pipeline["pa"]["summary"])
        st.json(pipeline["pa"]["dimension_scores"])

    st.markdown("### Synthese")
    st.write(pipeline["synthesis"]["combined_summary"])
    st.write(f"**Fokus:** {pipeline['synthesis']['priority_focus']}")
    st.write(f"**Empfehlung:** {pipeline['synthesis']['recommendation']}")


def _load_latest_catalog_for_answer_set(answer_set_id: str) -> str | None:
    with session_factory() as session:
        synthesis = session.scalar(
            select(SynthesisEntity)
            .where(SynthesisEntity.details["answer_set_id"].as_string() == answer_set_id)
            .order_by(SynthesisEntity.created_at.desc())
            .limit(1)
        )
        if synthesis is None:
            return None

        catalog = session.scalar(
            select(MeasureCatalogEntity)
            .where(MeasureCatalogEntity.details["synthesis_id"].as_string() == synthesis.synthesis_id)
            .order_by(MeasureCatalogEntity.created_at.desc())
            .limit(1)
        )

    return None if catalog is None else catalog.catalog_id


def _load_synthesis(synthesis_id: str) -> Synthesis | None:
    with session_factory() as session:
        entity = session.get(SynthesisEntity, synthesis_id)
    if entity is None:
        return None

    return Synthesis(
        synthesis_id=entity.synthesis_id,
        answer_set_id=entity.details.get("answer_set_id", ""),
        bi_assessment_id=entity.bi_assessment_id,
        pa_assessment_id=entity.pa_assessment_id,
        combined_summary=entity.details.get("combined_summary", ""),
        priority_focus=entity.details.get("priority_focus", ""),
        heuristic_reason=entity.details.get("heuristic_reason", ""),
        recommendation=entity.recommendation,
        model_version=entity.model_version,
        prompt_version=entity.prompt_version,
        created_at=entity.created_at,
    )


def _render_measures() -> None:
    st.subheader("Maßnahmen: Katalog, Auswahl, Priorisierung")
    answer_set_id = st.session_state["answer_set_id"]
    pipeline = st.session_state["pipeline"]
    if not answer_set_id or pipeline is None:
        st.warning("Bitte zuerst Ergebnisse berechnen.")
        return

    st.info("Standardmäßig wird eine lokale Ollama-Installation für Textverarbeitung genutzt (Fallback bei Nichterreichbarkeit).")

    if st.button("LLM/Ollama-Verbindung prüfen"):
        status = _build_llm_client().check_connection()
        if status.get("ok"):
            st.success(status.get("message", "LLM-Verbindung ist verfügbar."))
        else:
            st.error(status.get("message", "LLM-Verbindung ist nicht verfügbar."))
        st.caption(f"URL: {status.get('api_url', 'n/a')} | Modell: {status.get('model', 'n/a')} | Modus: {status.get('mode', 'n/a')}")

    if st.button("Maßnahmenkatalog generieren"):
        synthesis_payload = pipeline["synthesis"]
        synthesis_model = _load_synthesis(synthesis_payload["synthesis_id"])
        if synthesis_model is None:
            st.error("Synthese konnte nicht geladen werden. Bitte Ergebnisse neu berechnen.")
            return

        catalog = RecommendationService(llm_client=_build_llm_client()).generate_catalog(
            synthesis=synthesis_model,
            bi_maturity_label=pipeline["bi"]["level_label"],
            pa_maturity_label=pipeline["pa"]["level_label"],
            bi_dimension_scores=pipeline["bi"]["dimension_scores"],
            pa_dimension_scores=pipeline["pa"]["dimension_scores"],
            use_llm_texts=st.session_state.get("use_llm_texts", True),
            answers=st.session_state.get("answers", {}),
        )

        with session_factory() as session:
            PersistenceRepository(session).save_catalog(catalog)

        st.session_state["catalog_id"] = catalog.catalog_id
        st.success("Maßnahmenkatalog gespeichert.")

    if not st.session_state["catalog_id"]:
        st.session_state["catalog_id"] = _load_latest_catalog_for_answer_set(answer_set_id)

    catalog_id = st.session_state["catalog_id"]
    if not catalog_id:
        st.info("Noch kein Katalog vorhanden.")
        return

    with session_factory() as session:
        catalog = load_catalog(session, catalog_id)
    if catalog is None:
        st.error("Katalog konnte nicht geladen werden.")
        return

    editor_data = []
    for measure in catalog.measures:
        editor_data.append(
            {
                "measure_id": measure.measure_id,
                "initiative_id": measure.initiative_id,
                "titel": measure.title,
                "kategorie": measure.category.value,
                "impact": measure.impact,
                "effort": measure.effort,
                "ausgewählt": True,
                "endpriorität": measure.suggested_priority,
            }
        )

    st.write("Katalog bearbeiten:")
    if "selection_editor" in st.session_state and not isinstance(st.session_state["selection_editor"], dict):
        del st.session_state["selection_editor"]

    edited = st.data_editor(
        editor_data,
        use_container_width=True,
        num_rows="fixed",
        disabled=["measure_id", "initiative_id", "titel", "kategorie", "impact", "effort"],
        key="selection_editor",
    )

    if st.button("Finale Auswahl speichern"):
        selections = [row for row in edited if row.get("ausgewählt")]
        selected_ids = [row["measure_id"] for row in selections]
        final_priority = {
            row["measure_id"]: int(row["endpriorität"])
            for row in selections
            if row.get("endpriorität") is not None
        }

        with session_factory() as session:
            synthesis = session.scalar(
                select(SynthesisEntity)
                .where(SynthesisEntity.synthesis_id == catalog.synthesis_id)
                .limit(1)
            )
            if synthesis is None:
                st.error("Synthese für den Katalog nicht gefunden.")
                return

            selection = UserSelection(
                user_selection_id=f"sel-{uuid4().hex[:12]}",
                synthesis_id=synthesis.synthesis_id,
                catalog_id=catalog.catalog_id,
                selected_measure_ids=selected_ids,
                final_priority=final_priority,
            )
            PersistenceRepository(session).save_user_selection(selection)

        by_bucket = _build_catalog_summary_payload(catalog, selected_ids, final_priority)
        summary = _build_llm_client().summarize_measure_catalog(
            focus=str(pipeline["synthesis"].get("priority_focus", "")),
            measures_by_bucket=by_bucket,
        )
        st.session_state["catalog_summary"] = summary

        st.success("Finale Auswahl gespeichert.")

    if st.session_state.get("catalog_summary"):
        _render_catalog_summary(st.session_state["catalog_summary"])


def _build_catalog_summary_payload(catalog: object, selected_ids: list[str], final_priority: dict[str, int]) -> dict[str, list[dict[str, object]]]:
    selected = [measure for measure in catalog.measures if measure.measure_id in selected_ids]
    selected.sort(key=lambda measure: final_priority.get(measure.measure_id, measure.suggested_priority))

    by_bucket: dict[str, list[dict[str, object]]] = {"now": [], "next": [], "later": []}
    for measure in selected:
        bucket = str((measure.priority or {}).get("bucket", "later")).lower()
        if bucket not in by_bucket:
            bucket = "later"
        by_bucket[bucket].append(
            {
                "initiative_id": measure.initiative_id,
                "title": measure.title,
                "dimension": measure.dimension,
                "priority": final_priority.get(measure.measure_id, measure.suggested_priority),
                "dependencies": measure.dependencies,
                "deliverables": measure.deliverables[:3],
                "kpi": measure.kpi,
                "diagnosis": measure.description,
                "trigger_items": (measure.evidence or {}).get("trigger_items", [])[:3],
            }
        )
    return by_bucket


def _render_catalog_summary(summary: dict[str, object]) -> None:
    st.markdown("### Ergebnis Maßnahmenkatalog (LLM)")
    st.markdown(f"**{summary.get('headline', 'Ergebnis Maßnahmenkatalog')}**")
    st.write(summary.get("executive_summary", ""))

    col_now, col_next, col_later = st.columns(3)
    for column, key, title in (
        (col_now, "now", "Jetzt"),
        (col_next, "next", "Als Nächstes"),
        (col_later, "later", "Später"),
    ):
        with column:
            st.markdown(f"**{title}**")
            items = summary.get(key, [])
            if not items:
                st.caption("Keine Punkte")
            for item in items:
                st.markdown(f"- {item}")

    st.markdown("**Risiken & Abhängigkeiten**")
    for item in summary.get("risks_and_dependencies", []):
        st.markdown(f"- {item}")

    st.markdown("**Erste 30 Tage**")
    for item in summary.get("first_30_days", []):
        st.markdown(f"- {item}")

    details_by_bucket = summary.get("measure_details", {}) if isinstance(summary, dict) else {}
    if isinstance(details_by_bucket, dict):
        st.markdown("**Maßnahmen-Details (vollständig inkl. Evidenz-Trigger)**")
        for bucket, bucket_title in (("now", "Jetzt"), ("next", "Als Nächstes"), ("later", "Später")):
            entries = details_by_bucket.get(bucket, [])
            if not entries:
                continue
            st.markdown(f"_{bucket_title}_")
            for entry in entries:
                title = str(entry.get("title") or "Maßnahme")
                deliverables = entry.get("deliverables") if isinstance(entry.get("deliverables"), list) else []
                kpi_summary = str(entry.get("kpi_summary") or "")
                evidence_summary = str(entry.get("evidence_summary") or "")
                trigger_refs = entry.get("trigger_refs") if isinstance(entry.get("trigger_refs"), list) else []
                st.markdown(f"- **{title}**")
                for deliverable in deliverables:
                    st.markdown(f"  - Deliverable: {deliverable}")
                if kpi_summary:
                    st.markdown(f"  - KPI: {kpi_summary}")
                if evidence_summary:
                    st.markdown(f"  - Evidenz: {evidence_summary}")
                for trigger_ref in trigger_refs:
                    st.markdown(f"  - Trigger-Referenz: {trigger_ref}")

def _build_markdown_export(export_version: str) -> str:
    use_case_id = st.session_state["use_case_id"]
    answer_set_id = st.session_state["answer_set_id"]
    pipeline = st.session_state["pipeline"]
    catalog_id = st.session_state["catalog_id"]
    answers = st.session_state["answers"]

    if not (use_case_id and answer_set_id and pipeline):
        return "Noch keine vollständigen Daten für den Export vorhanden."

    with session_factory() as session:
        catalog = load_catalog(session, catalog_id) if catalog_id else None

    payload = build_export_payload(
        pipeline=pipeline,
        answers=answers,
        catalog=catalog,
        export_version=export_version,
        catalog_summary=st.session_state.get("catalog_summary"),
    )
    return payload_to_markdown(payload)


def _render_export() -> None:
    st.subheader("Export")
    export_version = st.selectbox(
        "Export-Version",
        options=["1.0.0", "1.1.0", "1.2.0"],
        index=1,
        help="1.0.0 bleibt unverändert, 1.1.0 bleibt verfügbar, 1.2.0 enthält Trigger-Evidenz, konkrete Deliverables und deterministische Buckets.",
    )

    markdown_payload = _build_markdown_export(export_version)

    use_case_id = st.session_state["use_case_id"]
    answer_set_id = st.session_state["answer_set_id"]
    pipeline = st.session_state["pipeline"]
    catalog_id = st.session_state["catalog_id"]
    answers = st.session_state["answers"]

    with session_factory() as session:
        catalog = load_catalog(session, catalog_id) if catalog_id else None

    json_payload = (
        payload_to_json(
            build_export_payload(
                pipeline=pipeline,
                answers=answers,
                catalog=catalog,
                export_version=export_version,
                catalog_summary=st.session_state.get("catalog_summary"),
            )
        )
        if (use_case_id and answer_set_id and pipeline)
        else "{}"
    )

    st.download_button(
        label="Markdown herunterladen",
        data=markdown_payload,
        file_name=f"insighthub_export_v{export_version}.md",
        mime="text/markdown",
    )
    st.download_button(
        label="JSON herunterladen",
        data=json_payload,
        file_name=f"insighthub_export_v{export_version}.json",
        mime="application/json",
    )

    st.text_area("Markdown-Vorschau", markdown_payload, height=320)


def main() -> None:
    _init_state()
    step = _render_header()

    if step == "Start":
        _render_start()
    elif step == "Fragebogen":
        _render_questionnaire()
    elif step == "Ergebnisse":
        _render_results()
    elif step == "Maßnahmen":
        _render_measures()
    elif step == "Export":
        _render_export()


if __name__ == "__main__":
    main()

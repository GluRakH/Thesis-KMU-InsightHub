from __future__ import annotations

import argparse

from domain.models import (
    Answer,
    AnswerSet,
    AnswerSetStatus,
    BIAssessment,
    CatalogStatus,
    Measure,
    MeasureCatalog,
    MeasureCategory,
    PAAssessment,
    Synthesis,
    UseCase,
    UseCaseType,
    UserSelection,
)
from persistence.database import Base, create_sqlite_engine, create_session_factory
from persistence.repositories import PersistenceRepository


def build_dummy_data() -> dict:
    use_case = UseCase(
        use_case_id="uc-001",
        name="Ticket Routing Assistant",
        description="KI-gestützte Priorisierung und Zuordnung von Support-Tickets.",
        use_case_type=UseCaseType.PROCESS_AUTOMATION,
    )
    answer_set = AnswerSet(
        answer_set_id="as-001",
        questionnaire_id="uc-001",
        status=AnswerSetStatus.SUBMITTED,
    )
    answers = [
        Answer(answer_id="a-001", answer_set_id="as-001", question_id="q-01", value="hoch"),
        Answer(answer_id="a-002", answer_set_id="as-001", question_id="q-02", value="mittel"),
    ]
    bi_assessment = BIAssessment(
        bi_assessment_id="bi-001",
        answer_set_id="as-001",
        score=78.5,
        summary="Hoher potenzieller Business Impact durch schnellere Bearbeitungszeiten.",
    )
    pa_assessment = PAAssessment(
        pa_assessment_id="pa-001",
        answer_set_id="as-001",
        score=71.0,
        summary="Prozess ist gut standardisierbar, Datenqualität ausreichend.",
    )
    synthesis = Synthesis(
        synthesis_id="syn-001",
        bi_assessment_id="bi-001",
        pa_assessment_id="pa-001",
        recommendation="Pilot mit zwei Support-Queues starten und KPI-Monitoring etablieren.",
    )
    catalog = MeasureCatalog(
        catalog_id="cat-001",
        title="Pilot-Maßnahmenkatalog",
        status=CatalogStatus.PUBLISHED,
        measures=[
            Measure(
                measure_id="m-001",
                title="Datenqualitäts-Check",
                description="Pflichtfelder und Label-Konsistenz vor dem Rollout absichern.",
                category=MeasureCategory.DATA,
            ),
            Measure(
                measure_id="m-002",
                title="Human-in-the-Loop",
                description="Fachteam bestätigt KI-Zuordnung in der Pilotphase.",
                category=MeasureCategory.GOVERNANCE,
            ),
        ],
    )
    user_selection = UserSelection(
        user_selection_id="sel-001",
        synthesis_id="syn-001",
        selected_measure_ids=["m-001", "m-002"],
    )

    return {
        "use_case": use_case,
        "answer_set": answer_set,
        "answers": answers,
        "bi_assessment": bi_assessment,
        "pa_assessment": pa_assessment,
        "synthesis": synthesis,
        "catalog": catalog,
        "user_selection": user_selection,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Persistenz-Demo für InsightHub")
    parser.add_argument("--db-path", default="data/insighthub.db", help="Pfad zur SQLite-Datei")
    args = parser.parse_args()

    engine = create_sqlite_engine(args.db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(args.db_path)

    dummy = build_dummy_data()

    with session_factory() as session:
        repository = PersistenceRepository(session)
        repository.create_use_case(dummy["use_case"])
        repository.save_answer_set(dummy["answer_set"], dummy["answers"])
        repository.save_assessments(dummy["bi_assessment"], dummy["pa_assessment"])
        repository.save_synthesis(dummy["synthesis"])
        repository.save_catalog(dummy["catalog"])
        repository.save_user_selection(dummy["user_selection"])

        loaded = repository.load_answer_set("as-001")

    if loaded is None:
        print("Fehler: Answer-Set konnte nicht geladen werden.")
        return

    loaded_set, loaded_answers = loaded
    print(f"Geladenes AnswerSet: {loaded_set.answer_set_id}, Status={loaded_set.status}")
    print("Antworten:")
    for answer in loaded_answers:
        print(f"- {answer.question_id}: {answer.value}")


if __name__ == "__main__":
    main()

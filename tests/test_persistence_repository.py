import tempfile
import unittest
from pathlib import Path

from domain.models import Answer, AnswerSet, AnswerSetStatus, BIAssessment, PAAssessment, Synthesis, UseCase, UseCaseType
from persistence.database import Base, create_sqlite_engine, create_session_factory
from persistence.repositories import PersistenceRepository


class PersistenceRepositoryTestCase(unittest.TestCase):
    def test_save_and_load_answer_set_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            engine = create_sqlite_engine(db_path)
            Base.metadata.create_all(engine)
            session_factory = create_session_factory(db_path)

            use_case = UseCase(
                use_case_id="uc-1",
                name="Support Triage",
                description="Auto classify inbound requests",
                use_case_type=UseCaseType.BUSINESS_IMPACT,
            )
            answer_set = AnswerSet(
                answer_set_id="as-1",
                questionnaire_id="uc-1",
                status=AnswerSetStatus.SUBMITTED,
            )
            answers = [
                Answer(answer_id="ans-1", answer_set_id="as-1", question_id="q-1", value="ja"),
                Answer(answer_id="ans-2", answer_set_id="as-1", question_id="q-2", value="nein"),
            ]

            with session_factory() as session:
                repository = PersistenceRepository(session)
                repository.create_use_case(use_case)
                repository.save_answer_set(answer_set, answers)
                loaded = repository.load_answer_set("as-1")

            self.assertIsNotNone(loaded)
            loaded_set, loaded_answers = loaded
            self.assertEqual(loaded_set.answer_set_id, "as-1")
            self.assertEqual(loaded_set.status, AnswerSetStatus.SUBMITTED)
            self.assertEqual(len(loaded_answers), 2)

    def test_persists_assessment_and_synthesis_versions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            engine = create_sqlite_engine(db_path)
            Base.metadata.create_all(engine)
            session_factory = create_session_factory(db_path)

            bi = BIAssessment(
                bi_assessment_id="bi-1",
                answer_set_id="as-1",
                score=2.5,
                summary="BI",
                questionnaire_version="v1.0",
                scoring_version="v1.0",
                prompt_version="scoring_v1.0",
                model_version="assessment-rules-v1",
            )
            pa = PAAssessment(
                pa_assessment_id="pa-1",
                answer_set_id="as-1",
                score=2.8,
                summary="PA",
                questionnaire_version="v1.0",
                scoring_version="v1.0",
                prompt_version="scoring_v1.0",
                model_version="assessment-rules-v1",
            )
            synthesis = Synthesis(
                synthesis_id="syn-1",
                answer_set_id="as-1",
                bi_assessment_id="bi-1",
                pa_assessment_id="pa-1",
                recommendation="Empfehlung",
                questionnaire_version="v1.0",
                scoring_version="v1.0",
                llm_model="gpt-4o-mini",
                llm_prompt_version="v1",
            )

            with session_factory() as session:
                repository = PersistenceRepository(session)
                repository.save_assessments(bi, pa)
                repository.save_synthesis(synthesis)

                loaded_assessments = repository.load_assessments_for_answer_set("as-1")
                loaded_synthesis = repository.load_latest_synthesis_for_answer_set("as-1")

            assert loaded_assessments is not None
            loaded_bi, loaded_pa = loaded_assessments
            assert loaded_synthesis is not None
            self.assertEqual(loaded_bi.scoring_version, "v1.0")
            self.assertEqual(loaded_pa.questionnaire_version, "v1.0")
            self.assertEqual(loaded_synthesis.llm_model, "gpt-4o-mini")
            self.assertEqual(loaded_synthesis.llm_prompt_version, "v1")


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from domain.models import Answer, AnswerSet, AnswerSetStatus, UseCase, UseCaseType
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


if __name__ == "__main__":
    unittest.main()

import unittest

from app.services.questionnaire_service import QuestionnaireService, ValidationStage


class QuestionnaireValidationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.service = QuestionnaireService()

    def test_required_null_errors_on_finalize(self) -> None:
        result = self.service.validate_answer_set("v1.0", {"CTX_01": None}, stage=ValidationStage.FINALIZE)
        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "REQUIRED_MISSING" for issue in result.issues))

    def test_likert_out_of_scale_errors(self) -> None:
        result = self.service.validate_answer_set("v1.0", {"CTX_01": 99}, stage=ValidationStage.FINALIZE)
        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "SCALE_OUT_OF_RANGE" for issue in result.issues))

    def test_single_choice_unknown_option_errors(self) -> None:
        # nutzt vorhandene SINGLE_CHOICE-Frage falls verfügbar, sonst wird unbekannte Frage markiert
        questionnaire = self.service.get_questionnaire("v1.0")
        q = next((item for item in questionnaire.questions if item.answer_type == "single_choice"), None)
        if q is None:
            self.skipTest("Keine SINGLE_CHOICE-Frage in v1.0 vorhanden")
        result = self.service.validate_answer_set("v1.0", {q.id: "invalid-option"}, stage=ValidationStage.FINALIZE)
        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "UNKNOWN_OPTION" for issue in result.issues))

    def test_text_whitespace_becomes_null_and_required_errors(self) -> None:
        questionnaire = self.service.get_questionnaire("v1.0")
        q = next((item for item in questionnaire.questions if item.answer_type == "text" and item.required), None)
        if q is None:
            self.skipTest("Keine required TEXT-Frage in v1.0 vorhanden")
        result = self.service.validate_answer_set("v1.0", {q.id: "   "}, stage=ValidationStage.FINALIZE)
        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "REQUIRED_MISSING" for issue in result.issues))


if __name__ == "__main__":
    unittest.main()

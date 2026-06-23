from cc_common.exceptions import CCInternalException
from cc_common.license_recognition_util import LBSW, LicenseRecognitionUtil

from tests import TstLambdas


class TestLicenseRecognitionUtil(TstLambdas):
    def test_recognized_license_type_returns_true_for_valid_jurisdiction_and_license_type(self):
        self.assertTrue(LicenseRecognitionUtil.license_type_is_recognized_in_jurisdiction('socw', 'al', LBSW))

    def test_unrecognized_license_type_returns_false_when_license_type_is_not_recognized_in_jurisdiction(self):
        self.assertFalse(LicenseRecognitionUtil.license_type_is_recognized_in_jurisdiction('socw', 'wa', LBSW))
        self.assertFalse(LicenseRecognitionUtil.license_type_is_recognized_in_jurisdiction('socw', 'co', LBSW))

    def test_inputs_are_case_insensitive(self):
        self.assertTrue(LicenseRecognitionUtil.license_type_is_recognized_in_jurisdiction('SOCW', 'AL', 'LBSW'))
        self.assertFalse(LicenseRecognitionUtil.license_type_is_recognized_in_jurisdiction('SOCW', 'WA', 'LBSW'))

    def test_missing_compact_raises(self):
        with self.assertRaises(CCInternalException) as ctx:
            LicenseRecognitionUtil.license_type_is_recognized_in_jurisdiction('unknown', 'al', LBSW)
        self.assertIn('compact', ctx.exception.message)

    def test_missing_jurisdiction_raises(self):
        with self.assertRaises(CCInternalException) as ctx:
            LicenseRecognitionUtil.license_type_is_recognized_in_jurisdiction('socw', 'zz', LBSW)
        self.assertIn('jurisdiction', ctx.exception.message)

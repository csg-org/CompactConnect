from unittest import TestCase

from common_constructs.security_profile import SecurityProfile


class TestSecurityProfile(TestCase):
    def test_recommended_value_is_one(self):
        self.assertEqual(1, SecurityProfile.RECOMMENDED.value)

    def test_vulnerable_value_is_two(self):
        self.assertEqual(2, SecurityProfile.VULNERABLE.value)

    def test_members_are_stable(self):
        self.assertEqual({'RECOMMENDED', 'VULNERABLE'}, {m.name for m in SecurityProfile})

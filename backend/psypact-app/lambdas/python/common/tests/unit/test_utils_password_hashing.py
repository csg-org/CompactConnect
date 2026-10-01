import unittest


class TestPasswordHashing(unittest.TestCase):
    """Test cases for password hashing utilities."""

    def test_hash_password_returns_different_hash_each_time(self):
        """Test that hashing the same password twice produces different hashes (due to salt)."""
        from cc_common.utils import hash_password

        password = 'test_recovery_token_123'  # noqa: S105 mock password
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        self.assertNotEqual(hash1, hash2)
        self.assertTrue(hash1.startswith('$argon2id$'))
        self.assertTrue(hash2.startswith('$argon2id$'))

    def test_verify_password_with_correct_password(self):
        """Test that verify_password returns True for correct password."""
        from cc_common.utils import hash_password, verify_password

        password = 'test_recovery_token_456'  # noqa: S105 mock password
        hashed = hash_password(password)

        result = verify_password(hashed, password)
        self.assertTrue(result)

    def test_verify_password_with_incorrect_password(self):
        """Test that verify_password returns False for incorrect password."""
        from cc_common.utils import hash_password, verify_password

        password = 'test_recovery_token_789'  # noqa: S105 mock password
        wrong_password = 'wrong_password'  # noqa: S105 mock password
        hashed = hash_password(password)

        result = verify_password(hashed, wrong_password)
        self.assertFalse(result)

    def test_verify_password_with_empty_password(self):
        """Test that verify_password returns False for empty password."""
        from cc_common.utils import hash_password, verify_password

        password = 'test_recovery_token_000'  # noqa: S105 mock password
        hashed = hash_password(password)

        result = verify_password(hashed, '')
        self.assertFalse(result)

    def test_hash_password_handles_special_characters(self):
        """Test that hashing works with special characters."""
        from cc_common.utils import hash_password, verify_password

        password = 'test_token_!@#$%^&*()_+-=[]{}|;:,.<>?'  # noqa: S105 mock password
        hashed = hash_password(password)

        result = verify_password(hashed, password)
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()

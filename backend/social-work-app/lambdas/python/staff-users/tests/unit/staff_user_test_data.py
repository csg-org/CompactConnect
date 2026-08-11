"""Helpers for building staff users and directories in unit tests.

Imports of cc_common are deferred into the functions so that the test base class can monkey-patch the
config object from its environment before anything reads it.
"""

from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

DEFAULT_LAST_LOGIN_AT = '2024-11-08T12:00:00+00:00'
ITERATE_USERS = 'cc_common.data_model.user_client.UserClient.iterate_all_users_in_compact'


def build_staff_user(
    *,
    last_login_at: str | None = DEFAULT_LAST_LOGIN_AT,
    status: str | None = None,
    compact_actions: set | None = None,
    jurisdictions: dict | None = None,
):
    """Build a StaffUserData. Pass last_login_at=None for a user who has never signed in."""
    from cc_common.data_model.schema.common import StaffUserStatus
    from cc_common.data_model.schema.user import StaffUserData
    from common_test.test_constants import DEFAULT_FAMILY_NAME, DEFAULT_GIVEN_NAME
    from common_test.test_data_generator import TestDataGenerator

    user_id = str(uuid4())
    staff_user = TestDataGenerator.generate_default_staff_user(
        {
            'userId': user_id,
            'status': status or StaffUserStatus.ACTIVE.value,
            'lastLoginAt': datetime.fromisoformat(last_login_at or DEFAULT_LAST_LOGIN_AT),
            # Each user needs a distinct email, or assertions on recipient sets pass no matter which
            # users the code picked
            'attributes': {
                'email': f'{user_id}@example.com',
                'givenName': DEFAULT_GIVEN_NAME,
                'familyName': DEFAULT_FAMILY_NAME,
            },
            'permissions': {
                'actions': compact_actions or set(),
                'jurisdictions': jurisdictions or {},
            },
        }
    )
    if last_login_at is not None:
        return staff_user

    # A user who has not signed in since login tracking was introduced has no lastLoginAt at all
    record = staff_user.serialize_to_database_record()
    del record['lastLoginAt']
    return StaffUserData.from_database_record(record)


def build_directory(users, *, compact: str = 'socw'):
    """Build a CompactStaffUserDirectory over the given users, without touching DynamoDB."""
    from staff_user_directory import CompactStaffUserDirectory

    with patch(ITERATE_USERS, return_value=iter(users)):
        return CompactStaffUserDirectory(compact=compact)

# ruff: noqa: T201 we use print statements for smoke testing
#!/usr/bin/env python3
"""
Smoke tests for staff user inactivity notifications and deactivation.

Walks one staff user through the whole inactivity lifecycle by moving their lastLoginAt backwards and
invoking the scheduled handler for each reminder type:

    51 days dormant  -> 10-day notice
    58 days dormant  ->  3-day notice
    60 days dormant  ->  1-day notice, on the user's last usable day, while they can still act on it
    61 days dormant  -> the account is deactivated, with no further notice

This is primarily a developer-verified test: CompactConnect reporting a send as successful only means SES
accepted it, not that the message arrived or reads correctly, so each notice-producing phase pauses and
asks the developer to check two inboxes before continuing:

    - the staff user's own address, CC_TEST_SMOKE_TEST_NOTIFICATION_EMAIL
    - a state admin address built by adding a "+state+admin" suffix to that same address, so both land
      in the same real mailbox as distinguishable messages

That check can still fail through no fault of this test, though: all of a jurisdiction's admins are
notified in a single combined send (one email, several recipients), and SES can reject the whole send if
any one recipient is not a real, deliverable, or verified address - not just the offending one. If
STAFF_USER_INACTIVITY_SMOKE_JURISDICTION already has another staff admin in that environment with a bad
address, the email will fail to send. Pick a jurisdiction with no other staff users in the environment
you are running against, and change the constant below if needed.

WARNING - Only run this test against testing environments. Invoking the handler runs it against every
staff user in the compact, not just the test user. The day-of invocation is a sweep, so any other staff
user in that environment who has been dormant for more than the inactivity period will be notified and
deactivated too.

Because of that, the metric assertions below are deliberately lower bounds rather than exact counts -
other users may legitimately appear in the same run. The test user's own outcome is verified directly
against Cognito and DynamoDB.

Both staff users created here - and their DynamoDB records - are always cleaned up, pass or fail.
"""

import json
from datetime import UTC, datetime, timedelta

from smoke_common import (
    SmokeTestFailureException,
    config,
    create_test_staff_user,
    delete_test_staff_user,
    get_lambda_client,
    load_smoke_test_env,
    logger,
)

STAFF_USER_INACTIVITY_SMOKE_COMPACT = 'socw'
# Must have no other staff users in the environment this runs against - see the module docstring for why
# a pre-existing admin with a bad address here would fail the adminEmailsSent check.
STAFF_USER_INACTIVITY_SMOKE_JURISDICTION = 'wa'

# The handler deactivates the day after the inactivity period elapses, so the user keeps all of day 60.
INACTIVITY_PERIOD_DAYS = 60
DAYS_TO_DEACTIVATION = INACTIVITY_PERIOD_DAYS + 1


def _state_admin_email(staff_user_email: str) -> str:
    """Build a distinguishable admin address that still lands in the same real mailbox.

    Most mail providers, including the ones these smoke test env files already use, deliver a
    "local+anything@domain" address to the same inbox as "local@domain".
    """
    local, domain = staff_user_email.split('@', 1)
    return f'{local}+state+admin@{domain}'


def _set_last_login_days_ago(user_sub: str, days_ago: int) -> None:
    """Move the user's lastLoginAt back far enough to land them in the cohort we want to exercise."""
    last_login_at = (datetime.now(tz=UTC) - timedelta(days=days_ago)).isoformat()
    logger.info(f'Setting lastLoginAt to {days_ago} days ago ({last_login_at})')
    config.staff_users_dynamodb_table.update_item(
        Key={'pk': f'USER#{user_sub}', 'sk': f'COMPACT#{STAFF_USER_INACTIVITY_SMOKE_COMPACT}'},
        UpdateExpression='SET lastLoginAt = :lastLoginAt',
        ExpressionAttributeValues={':lastLoginAt': last_login_at},
    )


def _invoke_inactivity_handler(days_before_deactivation: int) -> dict:
    """Invoke the scheduled handler exactly as its EventBridge rule would, and return its metrics."""
    logger.info(f'Invoking staff user inactivity handler with daysBeforeDeactivation={days_before_deactivation}')
    response = get_lambda_client().invoke(
        FunctionName=config.staff_user_inactivity_lambda_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(
            {
                'compact': STAFF_USER_INACTIVITY_SMOKE_COMPACT,
                'daysBeforeDeactivation': days_before_deactivation,
            }
        ),
    )

    payload = json.loads(response['Payload'].read())
    if response.get('FunctionError'):
        raise SmokeTestFailureException(f'Inactivity handler failed: {payload}')

    logger.info(f'Handler returned metrics: {payload["metrics"]}')
    return payload['metrics']


def _prompt_developer_to_verify_email(description: str, *, user_email: str, admin_email: str) -> None:
    """Ask the developer to confirm the notice actually arrived and reads correctly.

    A successful send just means SES accepted the message - it does not prove delivery or content, so a
    human has to look. A "n" answer fails the test via SmokeTestFailureException, same as any other
    assertion here, so the run still reaches main()'s finally block and cleans up both test users.
    """
    print('\n' + '=' * 78)
    print(f'MANUAL VERIFICATION NEEDED: {description}')
    print(f'  Staff user inbox : {user_email}')
    print(f'  State admin inbox: {admin_email}')
    print('  (Both addresses route to the same mailbox via the "+" suffix.)')
    print('=' * 78)
    answer = input('Did both emails arrive and read as expected? [y/n]: ').strip().lower()
    if answer != 'y':
        raise SmokeTestFailureException(f'Developer did not confirm {description} - check the inboxes above')


def _verify_notified(metrics: dict, *, run_description: str, user_email: str, admin_email: str) -> None:
    """Check that CompactConnect attempted to notify the test user and at least one state admin, then
    have the developer confirm the emails actually arrived.

    Lower bounds, not exact counts: other staff users in the environment may be in the same cohort. The
    test user's lastLoginAt was just moved to a date they have never been notified for, so the tracker
    cannot suppress their notice - at least one send must be reported for each audience.
    """
    if metrics['matchedUsers'] < 1:
        raise SmokeTestFailureException(f'Expected the test user in the {run_description} cohort, got: {metrics}')
    if metrics['userEmailsSent'] < 1:
        raise SmokeTestFailureException(f'Expected a notice addressed to the test user, got: {metrics}')
    if metrics['adminEmailsSent'] < 1:
        raise SmokeTestFailureException(f'Expected a notice addressed to a state admin, got: {metrics}')

    _prompt_developer_to_verify_email(f'the {run_description} notice', user_email=user_email, admin_email=admin_email)


def _get_user_status(user_sub: str) -> str:
    record = config.staff_users_dynamodb_table.get_item(
        Key={'pk': f'USER#{user_sub}', 'sk': f'COMPACT#{STAFF_USER_INACTIVITY_SMOKE_COMPACT}'}
    ).get('Item')
    if record is None:
        raise SmokeTestFailureException('Test staff user record is missing from DynamoDB')
    return record['status']


def _is_cognito_user_enabled(email: str) -> bool:
    user_data = config.cognito_client.admin_get_user(
        UserPoolId=config.cognito_staff_user_pool_id,
        Username=email,
    )
    return user_data['Enabled']


def test_ten_day_notice(user_sub: str, email: str, admin_email: str):
    """A user 51 days dormant is 10 days from deactivation."""
    _set_last_login_days_ago(user_sub, DAYS_TO_DEACTIVATION - 10)

    metrics = _invoke_inactivity_handler(10)

    _verify_notified(metrics, run_description='10-day', user_email=email, admin_email=admin_email)
    if metrics['deactivated'] != 0:
        raise SmokeTestFailureException(f'The 10-day run must not deactivate anyone, got: {metrics}')

    logger.info('10-day notice sent as expected')


def test_three_day_notice(user_sub: str, email: str, admin_email: str):
    """A user 58 days dormant is 3 days from deactivation."""
    _set_last_login_days_ago(user_sub, DAYS_TO_DEACTIVATION - 3)

    metrics = _invoke_inactivity_handler(3)

    _verify_notified(metrics, run_description='3-day', user_email=email, admin_email=admin_email)
    if metrics['deactivated'] != 0:
        raise SmokeTestFailureException(f'The 3-day run must not deactivate anyone, got: {metrics}')

    logger.info('3-day notice sent as expected')


def test_one_day_notice(user_sub: str, email: str, admin_email: str):
    """The 1-day notice arrives on the user's last usable day, and does not deactivate them."""
    _set_last_login_days_ago(user_sub, INACTIVITY_PERIOD_DAYS)

    metrics = _invoke_inactivity_handler(1)

    _verify_notified(metrics, run_description='1-day', user_email=email, admin_email=admin_email)
    if metrics['deactivated'] != 0:
        raise SmokeTestFailureException(f'The 1-day run must not deactivate anyone, got: {metrics}')
    if not _is_cognito_user_enabled(email):
        raise SmokeTestFailureException(
            f'The test user was disabled after only {INACTIVITY_PERIOD_DAYS} days - they should keep their final day'
        )
    if _get_user_status(user_sub) != 'active':
        raise SmokeTestFailureException(f'The test user was marked inactive after only {INACTIVITY_PERIOD_DAYS} days')

    logger.info(f'1-day notice sent at {INACTIVITY_PERIOD_DAYS} days dormant, without deactivating')


def test_day_of_deactivation_without_a_notice(user_sub: str, email: str):
    """One day further on, the user is deactivated. The 1-day run already sent the last notice, so the
    day-of run must not send another - nothing to manually verify here."""
    _set_last_login_days_ago(user_sub, DAYS_TO_DEACTIVATION)

    metrics = _invoke_inactivity_handler(0)

    if metrics['deactivated'] < 1:
        raise SmokeTestFailureException(f'Expected the test user to be deactivated, got: {metrics}')
    if metrics['userEmailsSent'] != 0 or metrics['adminEmailsSent'] != 0:
        raise SmokeTestFailureException(f'The day-of run must not send a notice, got: {metrics}')

    if _is_cognito_user_enabled(email):
        raise SmokeTestFailureException('The test user is still enabled in Cognito after deactivation')
    if _get_user_status(user_sub) != 'inactive':
        raise SmokeTestFailureException('The test user record was not marked inactive after deactivation')

    logger.info('Account was deactivated, with no further notice, in both Cognito and DynamoDB')


def main():
    load_smoke_test_env()

    email = config.smoke_test_notification_email
    admin_email = _state_admin_email(email)
    user_sub = None
    admin_sub = None

    try:
        # A state admin for the same jurisdiction, so resolve_admin_recipients has someone real to find
        # instead of falling back to compact admins already in the shared environment
        admin_sub = create_test_staff_user(
            email=admin_email,
            compact=STAFF_USER_INACTIVITY_SMOKE_COMPACT,
            jurisdiction=STAFF_USER_INACTIVITY_SMOKE_JURISDICTION,
            permissions={'jurisdictions': {STAFF_USER_INACTIVITY_SMOKE_JURISDICTION: {'admin'}}},
            suppress_welcome_message=True,
        )
        user_sub = create_test_staff_user(
            email=email,
            compact=STAFF_USER_INACTIVITY_SMOKE_COMPACT,
            jurisdiction=STAFF_USER_INACTIVITY_SMOKE_JURISDICTION,
            permissions={'jurisdictions': {STAFF_USER_INACTIVITY_SMOKE_JURISDICTION: {'write'}}},
            suppress_welcome_message=True,
        )

        test_ten_day_notice(user_sub, email, admin_email)
        test_three_day_notice(user_sub, email, admin_email)
        test_one_day_notice(user_sub, email, admin_email)
        test_day_of_deactivation_without_a_notice(user_sub, email)

    except Exception as e:
        logger.error(f'Staff user inactivity smoke tests failed: {str(e)}')
        raise
    finally:
        if user_sub:
            delete_test_staff_user(email, user_sub, STAFF_USER_INACTIVITY_SMOKE_COMPACT)
        if admin_sub:
            delete_test_staff_user(admin_email, admin_sub, STAFF_USER_INACTIVITY_SMOKE_COMPACT)

    logger.info('All staff user inactivity smoke tests passed!')


if __name__ == '__main__':
    main()

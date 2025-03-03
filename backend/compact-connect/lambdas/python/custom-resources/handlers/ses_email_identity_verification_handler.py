#!/usr/bin/env python3
import json
import time

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import logger
from cc_common.exceptions import CCInternalException


def on_event(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    CloudFormation event handler using the CDK provider framework.

    This custom resource verifies that a SES email identity is verified. It is used to
    prevent a race cobefore allowing
    dependent resources (like Cognito user pools) to be created. It polls the SES API
    until the identity is verified or until the Lambda times out.

    The function will:
    - Return successfully if the domain is verified
    - Raise an exception if verification fails or times out
    - Do nothing on Delete events

    :param event: The CloudFormation custom resource event
    :param context: The Lambda context
    :return: Physical resource ID on success
    """
    logger.info('Entering SES email identity verification handler', event=json.dumps(event))
    properties = event['ResourceProperties']
    request_type = event['RequestType']
    match request_type:
        case 'Create':
            return verify_ses_email_identity(properties)
        case 'Update' | 'Delete':
            # In the case of update or delete we do not need to verify the SES identity
            return None
        case _:
            raise ValueError(f'Unexpected request type: {request_type}')


# Extract properties from the event
def verify_ses_email_identity(properties: dict):
    domain_name = properties.get('DomainName')

    # Create SES client
    ses_client = boto3.client('ses')

    # Maximum number of attempts (15 seconds * 60 = 15 minutes)
    max_attempts = 60
    attempts = 0

    # Poll until the identity is verified or we time out
    while attempts < max_attempts:
        # Check verification status
        response = ses_client.get_identity_verification_attributes(Identities=[domain_name])

        # Get verification status
        attributes = response.get('VerificationAttributes', {})
        domain_attributes = attributes.get(domain_name, {})
        verification_status = domain_attributes.get('VerificationStatus', 'NotStarted')

        logger.info(f'Verification status for {domain_name}: {verification_status}')

        # If verified, we're done
        if verification_status == 'Success':
            logger.info(f'Domain {domain_name} is verified!')
            return

        # If failed, raise exception
        if verification_status == 'Failed':
            error_msg = f'Domain {domain_name} verification failed'
            logger.error(error_msg)
            raise CCInternalException(error_msg)

        # Wait and try again
        attempts += 1
        logger.info(f'Waiting for verification... Attempt {attempts}/{max_attempts}')
        time.sleep(15)  # Wait 15 seconds between checks

    # If we get here, we've timed out
    error_msg = f'Timed out waiting for domain {domain_name} to be verified'
    logger.error(error_msg)
    raise CCInternalException(error_msg)

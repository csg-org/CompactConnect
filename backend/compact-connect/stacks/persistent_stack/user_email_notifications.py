import os

from aws_cdk import CustomResource, Duration
from aws_cdk.aws_iam import PolicyStatement, ServicePrincipal
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.aws_route53 import IHostedZone, TxtRecord
from aws_cdk.aws_ses import ConfigurationSet, EmailIdentity, EmailSendingEvent, EventDestination, Identity
from aws_cdk.aws_sns import Subscription, SubscriptionProtocol, Topic
from aws_cdk.custom_resources import Provider
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack
from constructs import Construct


class UserEmailNotifications(Construct):
    """This Construct leverages SES to set up an email notification system to send cognito user events from our custom
    domain with necessary SPF, DKIM, and DMARC verification records.

    The topic is set up to forward all bounce and complaint events to the provided email address.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        hosted_zone: IHostedZone,
        environment_context: dict,
        master_key: IKey,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        domain_name = hosted_zone.zone_name
        operation_email = environment_context['notifications']['ses_operations_support_email']

        self.email_feedback_topic = Topic(
            self,
            'FeedbackTopic',
            display_name='Email Feedback Forwarding Topic',
            master_key=master_key,
            enforce_ssl=True,
        )
        Subscription(
            self,
            'FeedbackSubscription',
            topic=self.email_feedback_topic,
            protocol=SubscriptionProtocol.EMAIL,
            endpoint=operation_email,
        )

        self.config_set = ConfigurationSet(self, 'ConfigSet')

        self.config_set.add_event_destination(
            id='EmailFeedbackEventDestination',
            destination=EventDestination.sns_topic(self.email_feedback_topic),
            enabled=True,
            events=[EmailSendingEvent.BOUNCE, EmailSendingEvent.COMPLAINT],
        )

        ses_principal = ServicePrincipal('ses.amazonaws.com')
        self.email_feedback_topic.grant_publish(ses_principal)
        # grant SES the ability to encrypt bounce and complaint notifications using the KMS key
        master_key.grant_encrypt_decrypt(ses_principal)

        # Create SES Email Identity with DKIM enabled
        self.email_identity = EmailIdentity(
            self,
            'EmailIdentity',
            # by using the hosted zone resource, cdk will automatically
            # create all the necessary DNS records for DKIM and SPF authentication
            identity=Identity.public_hosted_zone(hosted_zone),
            mail_from_domain=f'no-reply.{domain_name}',
            configuration_set=self.config_set,
        )
        # grant cognito the ability to send email from this identity
        self.email_identity.grant_send_email(ServicePrincipal('cognito-idp.amazonaws.com'))

        # Add DMARC record to Route 53 with policy set to 'reject'
        # this will cause email servers to reject emails that do not pass SPF and DKIM checks
        # see https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-dmarc.html
        self.dmarc_record = TxtRecord(
            self,
            'DMARCRecord',
            zone=hosted_zone,
            record_name=f'_dmarc.{domain_name}',
            values=[f'v=DMARC1;p=reject;rua=mailto:{operation_email}'],
        )

        # Create a custom resource that verifies the SES identity is verified
        self.verification_custom_resource = self._create_verification_custom_resource(domain_name)

        # Add dependencies to ensure the verification custom resource is created after the SES identity
        self.verification_custom_resource.node.add_dependency(self.email_identity)
        self.verification_custom_resource.node.add_dependency(self.dmarc_record)

    def _create_verification_custom_resource(self, domain_name: str) -> CustomResource:
        """Create a custom resource that verifies the SES identity is verified."""
        stack = Stack.of(self)

        # Create a Lambda function that checks the verification status of the SES identity
        verification_function = PythonFunction(
            self,
            'DomainVerificationFunction',
            lambda_dir='custom-resources',
            index=os.path.join('handlers', 'ses_email_identity_verification_handler.py'),
            handler='on_event',
            description='Verifies that a SES email identity is verified',
            timeout=Duration.minutes(15),  # Long timeout to allow for verification
            memory_size=128,
            log_retention=RetentionDays.ONE_DAY,
            environment={
                'DOMAIN_NAME': domain_name,
                **stack.common_env_vars,
            },
        )

        # Grant the Lambda function permission to check the verification status
        verification_function.add_to_role_policy(
            PolicyStatement(
                actions=['ses:GetIdentityVerificationAttributes'],
                resources=['*'],  # SES doesn't support resource-level permissions for this action
            )
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{verification_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what '
                    'this lambda needs to check SES identity verification status.',
                },
            ],
        )

        # Create a provider for the custom resource
        verification_provider = Provider(
            self,
            'VerificationProvider',
            on_event_handler=verification_function,
            log_retention=RetentionDays.ONE_DAY,
        )

        # Add suppressions for the provider
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{verification_provider.node.path}/framework-onEvent/Resource',
            [
                {'id': 'AwsSolutions-L1', 'reason': 'We do not control this runtime'},
                {
                    'id': 'HIPAA.Security-LambdaConcurrency',
                    'reason': 'This function is only run at deploy time, '
                    'by CloudFormation and has no need for concurrency limits.',
                },
                {
                    'id': 'HIPAA.Security-LambdaDLQ',
                    'reason': 'This is a synchronous function run at deploy time. It does not need a DLQ',
                },
                {
                    'id': 'HIPAA.Security-LambdaInsideVPC',
                    'reason': 'We may choose to move our lambdas into private VPC subnets in a future enhancement',
                },
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{verification_provider.node.path}/framework-onEvent/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically '
                    'what this lambda needs to check SES identity verification status.',
                },
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{verification_provider.node.path}/framework-onEvent/ServiceRole/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM4',
                    'appliesTo': [
                        'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                    ],
                    'reason': 'This policy is needed for the custom resource provider to manage the SES verification.',
                },
            ],
        )

        # Create the custom resource
        return CustomResource(
            self,
            'VerificationResource',
            resource_type='Custom::SESIdentityVerification',
            service_token=verification_provider.service_token,
            properties={
                'DomainName': domain_name,
            },
        )

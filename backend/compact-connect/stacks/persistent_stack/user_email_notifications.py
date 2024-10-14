from aws_cdk.aws_iam import ServicePrincipal
from aws_cdk.aws_ses import EmailIdentity, Identity, ConfigurationSet, EmailSendingEvent, EventDestination
from aws_cdk.aws_sns import Topic, Subscription, SubscriptionProtocol
from aws_cdk.aws_route53 import TxtRecord, IHostedZone
from aws_cdk.aws_kms import IKey

from constructs import Construct


class UserEmailNotifications(Construct):
    """
    This Construct leverages SES to set up an email notification system to send cognito user events from our custom
    domain with necessary SPF, DKIM, and DMARC verification records.

    The topic is set up to forward all bounce and complaint events to the provided email address.
    """
    def __init__(
            self, scope: Construct, construct_id: str, *,
            hosted_zone: IHostedZone,
            environment_context: dict,
            master_key: IKey,
            **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        domain_name = hosted_zone.zone_name
        operation_email = environment_context['notifications']['ses_operations_support_email']


        self.email_feedback_topic = Topic(self, "FeedbackTopic",
                                          display_name="Email Feedback Forwarding Topic",
                                          master_key=master_key,
                                          enforce_ssl=True,
                                          )
        Subscription(self, "FeedbackSubscription",
                     topic=self.email_feedback_topic,
                     protocol=SubscriptionProtocol.EMAIL,
                     endpoint=operation_email)

        self.config_set = ConfigurationSet(self, "ConfigSet")

        self.config_set.add_event_destination(id="EmailFeedbackEventDestination",
                                         destination=EventDestination.sns_topic(self.email_feedback_topic),
                                         enabled=True,
                                         events=[EmailSendingEvent.BOUNCE,
                                                 EmailSendingEvent.COMPLAINT]
                                         )

        ses_principal = ServicePrincipal("ses.amazonaws.com")
        self.email_feedback_topic.grant_publish(ses_principal)
        # grant SES the ability to encrypt bounce and complaint notifications using the KMS key
        master_key.grant_encrypt_decrypt(ses_principal)


        # Create SES Email Identity with DKIM enabled
        self.email_identity = EmailIdentity(self, "EmailIdentity",
            # by using the hosted zone resource, cdk will automatically
            # create all the necessary DNS records for DKIM and SPF authentication
            identity=Identity.public_hosted_zone(hosted_zone),
            mail_from_domain=f"no-reply.{domain_name}",
            configuration_set=self.config_set
        )
        # grant cognito the ability to send email from this identity
        self.email_identity.grant_send_email(ServicePrincipal("cognito-idp.amazonaws.com"))

        # Add DMARC record to Route 53 with policy set to 'reject'
        # this will cause email servers to reject emails that do not pass SPF and DKIM checks
        # see https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-dmarc.html
        self.dmarc_record = TxtRecord(self, "DMARCRecord",
                  zone=hosted_zone,
                  record_name=f"_dmarc.{domain_name}",
                  values=[f"v=DMARC1;p=reject;rua=mailto:{operation_email}"]
                  )

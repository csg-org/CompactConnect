from unittest import TestCase

from aws_cdk import App, Stack
from aws_cdk.assertions import Match, Template
from aws_cdk.aws_apigateway import RestApi
from aws_cdk.aws_logs import CfnLogGroup
from aws_cdk.aws_wafv2 import CfnLoggingConfiguration, CfnWebACL, CfnWebACLAssociation

from common_constructs.security_profile import SecurityProfile
from common_constructs.webacl import WebACL, WebACLRules, WebACLScope


class TestWebACL(TestCase):
    def setUp(self):
        self.app = App()
        # Pin account/region so log_group_name comparisons are stable.
        self.stack = Stack(self.app, 'TestStack', env={'account': '111122223333', 'region': 'us-east-1'})

    # --- security defaults --------------------------------------------------

    def test_recommended_profile_includes_rate_limit_and_crs_rules(self):
        WebACL(self.stack, 'ACL', security_profile=SecurityProfile.RECOMMENDED)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnWebACL.CFN_RESOURCE_TYPE_NAME,
            {
                'DefaultAction': {'Allow': {}},
                'Scope': 'REGIONAL',
                'Rules': Match.array_with(
                    [
                        Match.object_like({'Name': 'RateLimit', 'Action': {'Block': {}}}),
                        Match.object_like(
                            {
                                'Name': 'CRSRule',
                                'Statement': {
                                    'ManagedRuleGroupStatement': {
                                        'Name': 'AWSManagedRulesCommonRuleSet',
                                        'VendorName': 'AWS',
                                    }
                                },
                            }
                        ),
                    ]
                ),
            },
        )

    def test_vulnerable_profile_omits_rate_limit_rule(self):
        WebACL(self.stack, 'ACL', security_profile=SecurityProfile.VULNERABLE)

        template = Template.from_stack(self.stack)
        acls = template.find_resources(CfnWebACL.CFN_RESOURCE_TYPE_NAME)
        self.assertEqual(1, len(acls))
        (acl,) = acls.values()
        rule_names = {rule['Name'] for rule in acl['Properties']['Rules']}
        self.assertEqual({'CRSRule'}, rule_names)

    def test_crs_rule_overrides_body_size_restriction_to_count(self):
        """SizeRestrictions_BODY is overridden to Count so large license uploads are not blocked."""
        WebACL(self.stack, 'ACL')

        template = Template.from_stack(self.stack)
        (acl,) = template.find_resources(CfnWebACL.CFN_RESOURCE_TYPE_NAME).values()
        crs_rule = next(r for r in acl['Properties']['Rules'] if r['Name'] == 'CRSRule')
        overrides = crs_rule['Statement']['ManagedRuleGroupStatement']['RuleActionOverrides']
        size_override = next(o for o in overrides if o['Name'] == 'SizeRestrictions_BODY')
        self.assertIn('Count', size_override['ActionToUse'])

    def test_default_scope_is_regional(self):
        WebACL(self.stack, 'ACL')

        template = Template.from_stack(self.stack)
        (acl,) = template.find_resources(CfnWebACL.CFN_RESOURCE_TYPE_NAME).values()
        self.assertEqual('REGIONAL', acl['Properties']['Scope'])

    # --- logging guarantees -------------------------------------------------

    def test_logging_redacts_authorization_header(self):
        WebACL(self.stack, 'ACL')

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnLoggingConfiguration.CFN_RESOURCE_TYPE_NAME,
            {'RedactedFields': [{'SingleHeader': {'Name': 'Authorization'}}]},
        )

    def test_log_group_uses_one_month_retention_and_waf_prefix(self):
        WebACL(self.stack, 'ACL')

        template = Template.from_stack(self.stack)
        groups = template.find_resources(
            CfnLogGroup.CFN_RESOURCE_TYPE_NAME,
            props={'Properties': {'RetentionInDays': 30}},
        )
        self.assertEqual(1, len(groups))
        (group,) = groups.values()
        self.assertTrue(group['Properties']['LogGroupName'].startswith('aws-waf-logs-'))

    def test_logging_disabled_creates_no_log_group_or_logging_config(self):
        WebACL(self.stack, 'ACL', enable_acl_logging=False)

        template = Template.from_stack(self.stack)
        self.assertEqual({}, template.find_resources(CfnLoggingConfiguration.CFN_RESOURCE_TYPE_NAME))
        self.assertEqual({}, template.find_resources(CfnLogGroup.CFN_RESOURCE_TYPE_NAME))

    # --- scope guards -------------------------------------------------------

    def test_cloudfront_scope_outside_us_east_1_raises(self):
        bad_stack = Stack(self.app, 'BadRegion', env={'account': '111122223333', 'region': 'us-west-2'})
        with self.assertRaises(RuntimeError):
            WebACL(bad_stack, 'ACL', acl_scope=WebACLScope.CLOUDFRONT)

    # --- public API ---------------------------------------------------------

    def test_associate_stage_creates_webacl_association(self):
        acl = WebACL(self.stack, 'ACL')
        api = RestApi(self.stack, 'Api')
        api.root.add_method('GET')
        acl.associate_stage(api.deployment_stage)

        template = Template.from_stack(self.stack)
        template.resource_count_is(CfnWebACLAssociation.CFN_RESOURCE_TYPE_NAME, 1)

    def test_custom_rules_override_security_profile_defaults(self):
        only_crs = [WebACLRules.common_rule()]
        WebACL(self.stack, 'ACL', security_profile=SecurityProfile.RECOMMENDED, rules=only_crs)

        template = Template.from_stack(self.stack)
        (acl,) = template.find_resources(CfnWebACL.CFN_RESOURCE_TYPE_NAME).values()
        self.assertEqual(['CRSRule'], [rule['Name'] for rule in acl['Properties']['Rules']])

    def test_cloudwatch_metrics_enabled_on_acl_and_rules(self):
        WebACL(self.stack, 'ACL')

        template = Template.from_stack(self.stack)
        (acl,) = template.find_resources(CfnWebACL.CFN_RESOURCE_TYPE_NAME).values()
        self.assertTrue(acl['Properties']['VisibilityConfig']['CloudWatchMetricsEnabled'])
        for rule in acl['Properties']['Rules']:
            self.assertTrue(rule['VisibilityConfig']['CloudWatchMetricsEnabled'])

    def test_add_rule_appends_to_rules_list(self):
        acl = WebACL(self.stack, 'ACL', security_profile=SecurityProfile.VULNERABLE)
        initial_count = len(acl.rules)
        new_rule = WebACLRules.rate_limit_rule()
        acl.add_rule(new_rule)
        # Check that the rule is actually in the rules list after adding
        self.assertIn(new_rule, acl.rules)
        # Optionally still check the count as a secondary check
        self.assertEqual(initial_count + 1, len(acl.rules))

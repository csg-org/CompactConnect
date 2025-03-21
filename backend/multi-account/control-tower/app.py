#!/usr/bin/env python3
from aws_cdk import App, Environment
from stacks.bare_org_stack import BareOrgStack
from stacks.landing_zone_stack import LandingZoneStack
from stacks.organizational_controls_stack import OrganizationalControlsStack


class ControlTowerApp(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        env = Environment(account=self.node.get_context('account_id'), region=self.node.get_context('region'))

        tags = self.node.get_context('tags')
        self.bare_org_stack = BareOrgStack(
            self,
            'BareOrganization',
            env=env,
            tags=tags,
            account_name_prefix=self.node.get_context('account_name_prefix'),
            email_domain=self.node.get_context('email_domain'),
        )

        self.landing_zone_stack = LandingZoneStack(
            self,
            'LandingZone',
            env=env,
            tags=tags,
            bare_org_stack=self.bare_org_stack,
            governed_regions=self.node.get_context('governed_regions'),
        )

        self.controls_stack = OrganizationalControlsStack(
            self,
            'Controls',
            env=env,
            tags=tags,
            bare_org_stack=self.bare_org_stack,
        )


if __name__ == '__main__':
    app = ControlTowerApp()
    app.synth()

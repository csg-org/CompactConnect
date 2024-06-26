#!/usr/bin/env python3
from aws_cdk import App

from common_constructs.stack import StandardTags
from stacks.api_stack import ApiStack
from stacks.persistent_stack import PersistentStack
from stacks.ui_stack import UIStack


class LicensureApp(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        environment_name = self.node.get_context('environment_name')

        tags = self.node.get_context('tags')

        self.persistent_stack = PersistentStack(
            self, 'PersistentStack',
            standard_tags=StandardTags(
                **tags,
                environment=environment_name
            ),
            environment_name=environment_name
        )

        self.ui_stack = UIStack(
            self, 'UIStack',
            standard_tags=StandardTags(
                **tags,
                environment=environment_name
            ),
            persistent_stack=self.persistent_stack
        )

        self.api_stack = ApiStack(
            self, 'APIStack',
            standard_tags=StandardTags(
                **tags,
                environment=environment_name
            ),
            environment_name=environment_name,
            persistent_stack=self.persistent_stack
        )


if __name__ == '__main__':
    app = LicensureApp()
    app.synth()

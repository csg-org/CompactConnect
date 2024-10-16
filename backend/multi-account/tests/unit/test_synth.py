import json
from unittest import TestCase

from app import MultiAccountApp


class TestSynth(TestCase):
    def test_synth(self):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.example.json') as f:
            context.update(json.load(f))

        MultiAccountApp(context=context)

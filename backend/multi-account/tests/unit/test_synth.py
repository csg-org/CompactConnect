import json
from unittest import TestCase

from app import MultiAccountApp


class TestSynth(TestCase):
    def test_synth(self):
        with open('cdk.json', 'r') as f:
            context = json.load(f)['context']
        with open('cdk.context.example.json', 'r') as f:
            context.update(json.load(f))

        MultiAccountApp(context=context)

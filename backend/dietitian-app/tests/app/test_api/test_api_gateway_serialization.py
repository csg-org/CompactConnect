from aws_cdk.assertions import Template
from aws_cdk.aws_apigateway import CfnModel

from tests.app.test_api import TestApi


class TestApiGatewaySerialization(TestApi):
    """
    Ensure API Gateway models are created serially via DependsOn.

    Parallel CreateModel calls commonly hit account rate limits (429) on first deploy
    of a large RestApi (same approach as DiningOut's serializeModelCreation).
    """

    def _assert_single_predecessor_chain(self, resources: dict):
        logical_ids = set(resources.keys())
        self.assertGreater(len(logical_ids), 1)

        # Ignore DependsOn edges to non-models (e.g. the RestApi).
        predecessors = {}
        for logical_id, resource in resources.items():
            depends_on = resource.get('DependsOn', [])
            if isinstance(depends_on, str):
                depends_on = [depends_on]
            predecessors[logical_id] = [dep for dep in depends_on if dep in logical_ids]

        roots = [logical_id for logical_id, deps in predecessors.items() if not deps]
        self.assertEqual(len(roots), 1, f'Expected exactly one chain root, found {roots}')

        for logical_id, deps in predecessors.items():
            if logical_id == roots[0]:
                continue
            self.assertEqual(
                len(deps),
                1,
                f'{logical_id} should depend on exactly one peer in the chain, found {deps}',
            )

        successors = {logical_id: [] for logical_id in logical_ids}
        for logical_id, deps in predecessors.items():
            for predecessor in deps:
                successors[predecessor].append(logical_id)

        visited = []
        current = roots[0]
        while current is not None:
            self.assertNotIn(current, visited)
            visited.append(current)
            next_nodes = successors[current]
            self.assertLessEqual(len(next_nodes), 1)
            current = next_nodes[0] if next_nodes else None

        self.assertEqual(len(visited), len(logical_ids))
        self.assertEqual(set(visited), logical_ids)

    def test_api_stack_serializes_model_creation(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        template = Template.from_stack(api_stack)
        self._assert_single_predecessor_chain(template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME))

    def test_state_api_stack_serializes_model_creation(self):
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        template = Template.from_stack(state_api_stack)
        self._assert_single_predecessor_chain(template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME))

    def test_search_api_stack_serializes_model_creation(self):
        search_api_stack = self.app.sandbox_backend_stage.search_api_stack
        template = Template.from_stack(search_api_stack)
        self._assert_single_predecessor_chain(template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME))

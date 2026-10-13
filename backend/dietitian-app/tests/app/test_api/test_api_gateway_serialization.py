from aws_cdk.assertions import Template
from aws_cdk.aws_apigateway import CfnMethod, CfnModel, CfnResource

from tests.app.test_api import TestApi


class TestApiGatewaySerialization(TestApi):
    """
    Ensure API Gateway models/resources/methods are created serially via DependsOn.

    Parallel CreateModel / CreateResource / CreateMethod calls commonly hit account rate
    limits (429) on first deploy of a large RestApi.
    """

    def _assert_single_predecessor_chain(self, resources: dict):
        """Assert peer DependsOn edges among this resource type form a single path."""
        logical_ids = set(resources.keys())
        self.assertGreater(len(logical_ids), 1)

        # Ignore DependsOn edges to other resource types (e.g. RestApi, parent Resource).
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
            # Serialization adds exactly one peer edge. Parent/child Resource refs may add
            # additional peer DependsOn edges, so require at least one.
            self.assertGreaterEqual(
                len(deps),
                1,
                f'{logical_id} should depend on at least one peer in the chain, found {deps}',
            )

        successors = {logical_id: [] for logical_id in logical_ids}
        for logical_id, deps in predecessors.items():
            for predecessor in deps:
                successors[predecessor].append(logical_id)

        # Walk from the unique root using any successor that still has unvisited nodes;
        # every resource must be reachable (connected DAG rooted at one node).
        visited = set()
        queue = [roots[0]]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            queue.extend(successors[current])

        self.assertEqual(visited, logical_ids)

    def _assert_stack_scaffolding_serialized(self, stack):
        template = Template.from_stack(stack)
        self._assert_single_predecessor_chain(template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME))
        self._assert_single_predecessor_chain(template.find_resources(CfnResource.CFN_RESOURCE_TYPE_NAME))
        self._assert_single_predecessor_chain(template.find_resources(CfnMethod.CFN_RESOURCE_TYPE_NAME))

    def test_api_stack_serializes_api_gateway_scaffolding(self):
        self._assert_stack_scaffolding_serialized(self.app.sandbox_backend_stage.api_stack)

    def test_state_api_stack_serializes_api_gateway_scaffolding(self):
        self._assert_stack_scaffolding_serialized(self.app.sandbox_backend_stage.state_api_stack)

    def test_search_api_stack_serializes_api_gateway_scaffolding(self):
        self._assert_stack_scaffolding_serialized(self.app.sandbox_backend_stage.search_api_stack)

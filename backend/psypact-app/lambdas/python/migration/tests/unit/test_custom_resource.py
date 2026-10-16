from custom_resource_handler import CustomResourceHandler, CustomResourceResponse

from tests import TstLambdas


class TestMigration(CustomResourceHandler):
    """Test implementation of CustomResourceMigration."""

    def __init__(self, migration_name: str):
        super().__init__(migration_name)
        self.create_called = False
        self.update_called = False
        self.delete_called = False
        self.properties_received = None

    def on_create(self, properties: dict) -> CustomResourceResponse | None:  # noqa: ARG002
        self.create_called = True
        self.properties_received = properties
        return {'PhysicalResourceId': 'test-migration', 'Data': {'test': 'value'}}

    def on_update(self, properties: dict) -> CustomResourceResponse | None:  # noqa: ARG002
        self.update_called = True
        self.properties_received = properties
        return {'PhysicalResourceId': 'test-migration', 'Data': {'test': 'updated'}}

    def on_delete(self, properties: dict) -> CustomResourceResponse | None:  # noqa: ARG002
        self.delete_called = True
        self.properties_received = properties
        return {'PhysicalResourceId': 'test-migration', 'Data': {'test': 'delete'}}


class TestCustomResourceMigration(TstLambdas):
    """Tests for the CustomResourceMigration base class."""

    def setUp(self):
        self.migration = TestMigration('test-migration')

    def test_on_event_create(self):
        """Test that Create events are routed to on_create."""
        event = {'RequestType': 'Create', 'ResourceProperties': {'test': 'value'}}

        result = self.migration(event, self.mock_context)

        self.assertTrue(self.migration.create_called)
        self.assertFalse(self.migration.update_called)
        self.assertFalse(self.migration.delete_called)
        self.assertEqual(self.migration.properties_received, {'test': 'value'})
        self.assertEqual(result, {'PhysicalResourceId': 'test-migration', 'Data': {'test': 'value'}})

    def test_on_event_update(self):
        """Test that Update events are routed to on_update."""
        event = {'RequestType': 'Update', 'ResourceProperties': {'test': 'updated'}}

        result = self.migration(event, self.mock_context)

        self.assertFalse(self.migration.create_called)
        self.assertTrue(self.migration.update_called)
        self.assertFalse(self.migration.delete_called)
        self.assertEqual(self.migration.properties_received, {'test': 'updated'})
        self.assertEqual(result, {'PhysicalResourceId': 'test-migration', 'Data': {'test': 'updated'}})

    def test_on_event_delete(self):
        """Test that Delete events are routed to on_delete."""
        event = {'RequestType': 'Delete', 'ResourceProperties': {'test': 'delete'}}

        result = self.migration(event, self.mock_context)

        self.assertFalse(self.migration.create_called)
        self.assertFalse(self.migration.update_called)
        self.assertTrue(self.migration.delete_called)
        self.assertEqual(self.migration.properties_received, {'test': 'delete'})
        self.assertEqual(result, {'PhysicalResourceId': 'test-migration', 'Data': {'test': 'delete'}})

    def test_on_event_invalid_request_type(self):
        """Test that invalid request types raise ValueError."""
        event = {'RequestType': 'InvalidType', 'ResourceProperties': {}}

        with self.assertRaises(ValueError) as context:
            self.migration(event, self.mock_context)

        self.assertEqual(str(context.exception), 'Unexpected request type: InvalidType')

    def test_on_event_create_exception(self):
        """Test that exceptions in on_create are logged and re-raised."""
        event = {'RequestType': 'Create', 'ResourceProperties': {}}

        # Create a migration that raises an exception
        class ExceptionMigration(CustomResourceHandler):
            def on_create(self, _properties: dict):
                raise ValueError('Test exception')

            def on_update(self, _properties: dict):
                return None

            def on_delete(self, _properties: dict):
                return None

        migration = ExceptionMigration('exception-migration')

        with self.assertRaises(ValueError) as context:
            migration(event, self.mock_context)

        self.assertEqual(str(context.exception), 'Test exception')

    def test_on_event_update_exception(self):
        """Test that exceptions in on_update are logged and re-raised."""
        event = {'RequestType': 'Update', 'ResourceProperties': {}}

        # Create a migration that raises an exception
        class ExceptionMigration(CustomResourceHandler):
            def on_create(self, _properties: dict):
                return None

            def on_update(self, _properties: dict):
                raise ValueError('Test update exception')

            def on_delete(self, _properties: dict):
                return None

        migration = ExceptionMigration('exception-migration')

        with self.assertRaises(ValueError) as context:
            migration(event, self.mock_context)

        self.assertEqual(str(context.exception), 'Test update exception')

    def test_on_event_delete_exception(self):
        """Test that exceptions in on_delete are logged and re-raised."""
        event = {'RequestType': 'Delete', 'ResourceProperties': {}}

        # Create a migration that raises an exception
        class ExceptionMigration(CustomResourceHandler):
            def on_create(self, _properties: dict):
                return None

            def on_update(self, _properties: dict):
                return None

            def on_delete(self, _properties: dict):
                raise ValueError('Test delete exception')

        migration = ExceptionMigration('exception-migration')

        with self.assertRaises(ValueError) as context:
            migration(event, self.mock_context)

        self.assertEqual(str(context.exception), 'Test delete exception')

    def test_empty_resource_properties(self):
        """Test handling of events with no ResourceProperties."""
        event = {
            'RequestType': 'Create'
            # No ResourceProperties
        }

        result = self.migration(event, self.mock_context)

        self.assertTrue(self.migration.create_called)
        self.assertEqual(self.migration.properties_received, {})
        self.assertEqual(result, {'PhysicalResourceId': 'test-migration', 'Data': {'test': 'value'}})

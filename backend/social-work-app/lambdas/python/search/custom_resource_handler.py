#!/usr/bin/env python3
from abc import ABC, abstractmethod
from typing import TypedDict

from aws_lambda_powertools.logging.lambda_context import build_lambda_context_model
from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import logger


class CustomResourceResponse(TypedDict, total=False):
    """Return body for the custom resource handler."""

    PhysicalResourceId: str
    Data: dict
    NoEcho: bool


class CustomResourceHandler(ABC):
    """Base class for custom resource migrations.

    This class provides a framework for implementing CloudFormation custom resources.
    It handles the routing of CloudFormation events to appropriate methods and provides a consistent
    logging pattern.

    Subclasses must implement the on_create, on_update, and on_delete methods.

    Instances of this class are callable and can be used directly as Lambda handlers.
    """

    def __init__(self, handler_name: str):
        """Initialize the custom resource handler.

        :type handler_name: str
        """
        self.handler_name = handler_name

    def __call__(self, event: dict, _context: LambdaContext) -> CustomResourceResponse | None:
        return self._on_event(event, _context)

    def _on_event(self, event: dict, _context: LambdaContext) -> CustomResourceResponse | None:
        """CloudFormation event handler using the CDK provider framework.
        See: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.custom_resources/README.html

        This method routes the event to the appropriate handler method based on the request type.

        :param event: The lambda event with properties in ResourceProperties
        :type event: dict
        :param _context: Lambda context
        :type _context: LambdaContext
        :return: Optional result from the handler method
        :rtype: Optional[CustomResourceResponse]
        :raises ValueError: If the request type is not supported
        """

        # @logger.inject_lambda_context doesn't work on instance methods, so we'll build the context manually
        lambda_context = build_lambda_context_model(_context)
        logger.structure_logs(**lambda_context.__dict__)

        logger.info(f'{self.handler_name} handler started')

        properties = event.get('ResourceProperties', {})
        request_type = event['RequestType']

        match request_type:
            case 'Create':
                try:
                    resp = self.on_create(properties)
                except Exception as e:
                    logger.error(f'Error in {self.handler_name} creation', exc_info=e)
                    raise
            case 'Update':
                try:
                    resp = self.on_update(properties)
                except Exception as e:
                    logger.error(f'Error in {self.handler_name} update', exc_info=e)
                    raise
            case 'Delete':
                try:
                    resp = self.on_delete(properties)
                except Exception as e:
                    logger.error(f'Error in {self.handler_name} delete', exc_info=e)
                    raise
            case _:
                raise ValueError(f'Unexpected request type: {request_type}')

        logger.info(f'{self.handler_name} handler complete')
        return resp

    @abstractmethod
    def on_create(self, properties: dict) -> CustomResourceResponse | None:
        """Handle Create events.

        This method should be implemented by subclasses to perform the migration when a resource is being created.

        :param properties: The ResourceProperties from the CloudFormation event
        :type properties: dict
        :return: Any result to be returned to CloudFormation
        :rtype: Optional[CustomResourceResponse]
        """

    @abstractmethod
    def on_update(self, properties: dict) -> CustomResourceResponse | None:
        """Handle Update events.

        This method should be implemented by subclasses to perform the migration when a resource is being updated.

        :param properties: The ResourceProperties from the CloudFormation event
        :type properties: dict
        :return: Any result to be returned to CloudFormation
        :rtype: Optional[CustomResourceResponse]
        """

    @abstractmethod
    def on_delete(self, properties: dict) -> CustomResourceResponse | None:
        """Handle Delete events.

        This method should be implemented by subclasses to handle deletion of the migration. In many cases, this can
        be a no-op as the migration is temporary and deletion should have no effect.

        :param properties: The ResourceProperties from the CloudFormation event
        :type properties: dict
        :return: Any result to be returned to CloudFormation
        :rtype: Optional[CustomResourceResponse]
        """

import json
from base64 import b64encode

from botocore.exceptions import ClientError

from tests import TstLambdas


class TestPaginated(TstLambdas):
    def test_pagination_parameters(self):
        from data_model.client import paginated

        @paginated
        def get_something(*args, **kwargs):
            return {
                'Items': [
                    # Really, this would be actual db records, but we're just going
                    # to stash our args and kwargs here, so we can inspect what this
                    # function was called with
                    {
                        'args': args,
                        'kwargs': kwargs
                    }
                ],
                'LastEvaluatedKey': {
                    # Just to make sure we're handling non-ascii
                    'pk': 'gòrach',
                    'sk': 'aslp/co/license-home'
                },
            }

        resp = get_something(
            'arg1',
            'arg2',
            pagination={
                'last_key': b64encode(json.dumps({'pk': '안녕하세요', 'sk': '2'}).encode('utf-8')),
                'page_size': 5
            },
            kwarg1='baf'
        )

        self.assertEqual(
            {
                'items': [{
                    'args': ('arg1', 'arg2'),
                    'kwargs': {
                        'kwarg1': 'baf',
                        'dynamo_pagination': {
                            'ExclusiveStartKey': {
                                'pk': '안녕하세요',
                                'sk': '2'
                            },
                            'Limit': 5
                        }
                    }
                }],
                'lastKey': b64encode(
                    json.dumps({'pk': 'gòrach', 'sk': 'aslp/co/license-home'}).encode('utf-8')
                ).decode('ascii')
            },
            resp
        )

    def test_no_pagination_parameters(self):
        from data_model.client import paginated

        @paginated
        def get_something(*args, **kwargs):
            return {
                'Items': [
                    # Really, this would be actual db records, but we're just going
                    # to stash our args and kwargs here, so we can inspect what this
                    # function was called with
                    {
                        'args': args,
                        'kwargs': kwargs
                    }
                ]
            }

        resp = get_something()

        self.assertEqual(
            {
                'items': [{
                    'args': (),
                    'kwargs': {
                        'dynamo_pagination': {
                            # Should fall back to default from config
                            'Limit': 100
                        }
                    }
                }]
            },
            resp
        )

    def test_invalid_key(self):
        from data_model.client import paginated
        from exceptions import CCInvalidRequestException

        @paginated
        def get_something(*args, **kwargs):  # pylint: disable=unused-argument
            return {
                'Items': []
            }

        with self.assertRaises(CCInvalidRequestException):
            get_something(pagination={'last_key': 'not-b64-string'})

    def test_db_invalid_key(self):
        from data_model.client import paginated
        from exceptions import CCInvalidRequestException

        @paginated
        def throw_an_error(*args, **kwargs):
            # This is what dynamodb rejecting the ExclusiveStartKey looks like for boto3
            raise ClientError(
                error_response={
                    'Error': {
                        'Message': 'The provided starting key is invalid',
                        "Code": "ValidationException"
                    },
                    'ResponseMetadata': {
                        'RequestId': 'AQ43F939QGII7PJFDUT7K7K67RVV4KQNSO5AEMVJF66Q9ASUAAJG',
                        'HTTPStatusCode': 400,
                        'HTTPHeaders': {
                            'server': 'Server',
                            'date': 'Tue, 27 Jun 2024 22:06:20 GMT',
                            'content-type': 'application/x-amz-json-1.0',
                            'content-length': '107',
                            'connection': 'keep-alive',
                            'x-amzn-requestid': 'AQ43F939QGII7PJFDUT7K7K67RVV4KQNSO5AEMVJF66Q9ASUAAJG',
                            'x-amz-crc32': '1281463594'
                        },
                        'RetryAttempts': 0
                    }
                },
                operation_name='Query'
            )

        with self.assertRaises(CCInvalidRequestException):
            throw_an_error()

    def test_db_other_error(self):
        from data_model.client import paginated

        @paginated
        def throw_an_error(*args, **kwargs):
            # An AccessDeniedException, for example, should be re-raised
            raise ClientError(
                error_response={
                    'Error': {
                        'Message': 'User: arn:aws:sts::000011112222:assumed-role/SomeRole/session-id '
                                   'is not authorized to perform: dynamodb:GetItem on resource: '
                                   'arn:aws:dynamodb:us-east-1:000011112222:table/some-table with an explicit deny in'
                                   ' a resource-based policy',
                        'Code': 'AccessDeniedException'
                    },
                    'ResponseMetadata': {
                        'RequestId': 'EJFUNRLG2GF7OTHTFVO8P3ODBRVV4KQNSO5AEMVJF66Q9ASUAAJG',
                        'HTTPStatusCode': 400,
                        'HTTPHeaders': {
                            'server': 'Server',
                            'date': 'Mon, 01 Jul 2024 16:00:55 GMT',
                            'content-type': 'application/x-amz-json-1.0',
                            'content-length': '379',
                            'connection': 'keep-alive',
                            'x-amzn-requestid': 'EJFUNRLG2GF7OTHTFVO8P3ODBRVV4KQNSO5AEMVJF66Q9ASUAAJG',
                            'x-amz-crc32': '1682830636'
                        },
                        'RetryAttempts': 0
                    }
                },
                operation_name='Query'
            )

        with self.assertRaises(ClientError):
            throw_an_error()

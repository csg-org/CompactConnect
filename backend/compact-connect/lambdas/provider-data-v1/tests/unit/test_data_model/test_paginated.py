import json
from base64 import b64encode

from botocore.exceptions import ClientError

from tests import TstLambdas


class TestPaginated(TstLambdas):
    def setUp(self):  # pylint: disable=invalid-name
        with open('tests/resources/dynamo/provider.json', 'r') as f:
            self._item = json.load(f)

    def test_pagination_parameters(self):
        from data_model.query_paginator import paginated_query
        from data_model.schema.provider import ProviderRecordSchema

        calls = []

        @paginated_query
        def get_something(*args, **kwargs):
            calls.append((args, kwargs))
            return {
                'Items': [self._item],
                'Count': 5,
                'LastEvaluatedKey': {
                    'pk': self._item['pk'],
                    'sk': self._item['sk']
                }
            }

        last_key = b64encode(json.dumps({'pk': '안녕하세요', 'sk': '2'}).encode('utf-8'))
        resp = get_something(
            'arg1',
            'arg2',
            pagination={
                'lastKey': last_key,
                'pageSize': 5
            },
            kwarg1='baf'
        )

        self.assertEqual(
            {
                'items': [ProviderRecordSchema().load(self._item)],
                'pagination': {
                    'pageSize': 5,
                    'lastKey': b64encode(
                        json.dumps({'pk': self._item['pk'], 'sk': self._item['sk']}).encode('utf-8')
                    ).decode('ascii'),
                    'prevLastKey': last_key
                },
            },
            resp
        )
        # Check that the decorated function was called with the expected args
        self.assertEqual(
            [
                (
                    ('arg1', 'arg2'),
                    {
                        'kwarg1': 'baf',
                        'dynamo_pagination': {
                            'ExclusiveStartKey': {
                                'pk': '안녕하세요',
                                'sk': '2'
                            },
                            'Limit': 5
                        }
                    }
                )
            ],
            calls
        )

    def test_multiple_internal_pages(self):
        """
        In the case of server-side filtering, DynamoDB scans the Limit number of records but only returns records
        that match filter criteria, which can be fewer. In this case, paginated_query should automatically query
        multiple times to fill out the requested page size.
        """
        from data_model.query_paginator import paginated_query
        from data_model.schema.provider import ProviderRecordSchema

        calls = []

        @paginated_query
        def get_something(*args, **kwargs):
            """
            Pretend 4 items were filtered out
            """
            calls.append((args, kwargs))
            return {
                'Items': [self._item] * 6,
                'Count': 6,
                'LastEvaluatedKey': {
                    'pk': self._item['pk'],
                    'sk': self._item['sk']
                }
            }

        last_key = b64encode(json.dumps({'pk': '안녕하세요', 'sk': '2'}).encode('utf-8'))
        resp = get_something(
            'arg1',
            'arg2',
            pagination={
                'lastKey': last_key,
                'pageSize': 10
            },
            kwarg1='baf'
        )

        self.assertEqual(
            {
                # 12 items will have been returned from queries internally, but only 10 make it out
                # to fill out the pageSize
                'items': [ProviderRecordSchema().load(self._item)] * 10,
                'pagination': {
                    'pageSize': 10,
                    'lastKey': b64encode(
                        json.dumps({'pk': self._item['pk'], 'sk': self._item['sk']}).encode('utf-8')
                    ).decode('ascii'),
                    'prevLastKey': last_key
                },
            },
            resp
        )
        # 2 calls, each returning 6 items, will fill out the page size.
        self.assertEqual(
            [
                (
                    ('arg1', 'arg2'),
                    {
                        'kwarg1': 'baf',
                        'dynamo_pagination': {
                            'ExclusiveStartKey': {
                                'pk': '안녕하세요',
                                'sk': '2'
                            },
                            'Limit': 10
                        }
                    }
                ),
                (
                    ('arg1', 'arg2'),
                    {
                        'kwarg1': 'baf',
                        'dynamo_pagination': {
                            'ExclusiveStartKey': {
                                'pk': self._item['pk'],
                                'sk': self._item['sk']
                            },
                            'Limit': 10
                        }
                    }
                )
            ],
            calls
        )

    def test_no_pagination_parameters(self):
        from data_model.query_paginator import paginated_query
        from data_model.schema.provider import ProviderRecordSchema


        calls = []
        @paginated_query
        def get_something(*args, **kwargs):
            calls.append((args, kwargs))
            return {
                'Items': [self._item],
                'Count': 1
            }

        resp = get_something()

        self.assertEqual(
            {
                'items': [ProviderRecordSchema().load(self._item)],
                'pagination': {
                    'pageSize': 100,
                    'lastKey': None,
                    'prevLastKey': None
                }
            },
            resp
        )
        self.assertEqual(
            [(
                (),
                {
                    'dynamo_pagination': {
                        # Should fall back to default from config
                        'Limit': 100
                    }
                }
            )],
            calls
        )

    def test_invalid_key(self):
        from data_model.query_paginator import paginated_query
        from exceptions import CCInvalidRequestException

        @paginated_query
        def get_something(*args, **kwargs):  # pylint: disable=unused-argument
            return {
                'Items': [],
                'Count': 1
            }

        with self.assertRaises(CCInvalidRequestException):
            get_something(pagination={'lastKey': 'not-b64-string'})

    def test_db_invalid_key(self):
        from data_model.query_paginator import paginated_query
        from exceptions import CCInvalidRequestException

        @paginated_query
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
        from data_model.query_paginator import paginated_query

        @paginated_query
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

    def test_instance_method(self):
        """
        Decorating instance methods works slightly differently than functions, so we'll make sure our decorator works
        for both.
        """
        from data_model.query_paginator import paginated_query

        calls = []

        class SomeClient:
            def __init__(self, test_inst):
                self._provider = test_inst._item

            @paginated_query
            def get_something(self, *args, **kwargs):
                calls.append((args, kwargs))
                return {
                    'Items': [self._provider],
                    'Count': 5
                }

        last_key = b64encode(json.dumps({'pk': '안녕하세요', 'sk': '2'}).encode('utf-8'))
        SomeClient(self).get_something(
            'arg1',
            'arg2',
            pagination={
                'lastKey': last_key,
                'pageSize': 5
            },
            kwarg1='baf'
        )

        # Check that the decorated method was called with the expected args
        self.assertEqual(
            [
                (
                    ('arg1', 'arg2'),
                    {
                        'kwarg1': 'baf',
                        'dynamo_pagination': {
                            'ExclusiveStartKey': {
                                'pk': '안녕하세요',
                                'sk': '2'
                            },
                            'Limit': 5
                        }
                    }
                )
            ],
            calls
        )

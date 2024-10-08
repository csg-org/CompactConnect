import json
from base64 import b64encode

from aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event import TypeDeserializer
from botocore.exceptions import ClientError

from tests import TstLambdas


class TestPaginated(TstLambdas):
    def setUp(self):  # pylint: disable=invalid-name
        with open('tests/resources/dynamo/user.json', 'r') as f:
            self._item = TypeDeserializer().deserialize({'M': json.load(f)})

    def test_pagination_parameters(self):
        from data_model.query_paginator import paginated_query
        from data_model.schema.user import UserRecordSchema

        calls = []

        @paginated_query
        def get_something(*args, **kwargs):
            calls.append((args, kwargs))
            return {
                'Items': [self._item],
                'Count': 5,
                'LastEvaluatedKey': {
                    'pk': self._item['pk']
                }
            }

        last_key = b64encode(json.dumps({'pk': 'USER#a4182428-d061-701c-82e5-a3d1d547d797'}).encode('utf-8'))
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
                'items': [UserRecordSchema().load(self._item)],
                'pagination': {
                    'pageSize': 5,
                    'lastKey': b64encode(
                        json.dumps({'pk': self._item['pk']}).encode('utf-8')
                    ).decode('utf-8'),
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
                                'pk': 'USER#a4182428-d061-701c-82e5-a3d1d547d797'
                            },
                            'Limit': 5
                        }
                    }
                )
            ],
            calls
        )

    def test_multiple_internal_pages_server_filter(self):
        """
        In the case of server-side filtering, DynamoDB scans the Limit number of records but only returns records
        that match filter criteria, which can be fewer. In this case, paginated_query should automatically query
        multiple times to fill out the requested page size.
        """
        from data_model.query_paginator import paginated_query
        from data_model.schema.user import UserRecordSchema

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
                    'pk': self._item['pk']
                }
            }

        last_key = b64encode(json.dumps({'pk': 'USER#a4182428-d061-701c-82e5-a3d1d547d797'}).encode('utf-8'))
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
                'items': [UserRecordSchema().load(self._item)] * 10,
                'pagination': {
                    'pageSize': 10,
                    'lastKey': b64encode(
                        json.dumps({'pk': self._item['pk']}).encode('utf-8')
                    ).decode('utf-8'),
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
                                'pk': 'USER#a4182428-d061-701c-82e5-a3d1d547d797'
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
                                'pk': self._item['pk']
                            },
                            'Limit': 10
                        }
                    }
                )
            ],
            calls
        )

    def test_multiple_internal_pages_client_filter(self):
        """
        In the case of client-side filtering, DynamoDB may return the Limit of records, but a client-side filter may
        trim that number back below the Limit. In this case, paginated_query should automatically query multiple times
        to fill out the requested page size. Because of the complexity of this flow, we'll go out of our way to look
        closely at the last_key behavior between each query.
        """
        from data_model.query_paginator import paginated_query
        from data_model.schema.user import UserRecordSchema

        calls = []

        @paginated_query
        def get_something(*args, **kwargs):
            calls.append((args, kwargs))

            last_key = int(kwargs['dynamo_pagination'].get('ExclusiveStartKey', {}).get('pk', 0))
            resp = {
                'Items': [],
                'Count': 8,
            }
            # 8 items, starting after last_key
            for i in range(last_key+1, last_key+9):
                item = self._item.copy()
                # Number users to give us something simple to filter by
                item['pk'] = str(i)
                resp['Items'].append(item)

            resp['LastEvaluatedKey'] = {
                'pk': resp['Items'][-1]['pk']
            }
            return resp

        def filter_odd_users(item: dict) -> bool:
            # True for even numbers
            return int(item['pk']) % 2 == 0

        last_key = b64encode(json.dumps({'pk': '1'}).encode('utf-8'))
        resp = get_something(
            'arg1',
            'arg2',
            pagination={
                'lastKey': last_key,
                'pageSize': 10
            },
            client_filter=filter_odd_users,
            kwarg1='baf'
        )

        # We are requesting 10 users, starting with exclusive key 1, and filtering out all odds client-side. This
        # should result in three queries to the DB, with the last record included in the response having a pk of 20:
        #
        # | Query | DB sequence | PK | Ret Sequence |  Filter   | last_key |
        # |-------|-------------|----|--------------|-----------|----------|
        # |   1   |     1       |  2 |      1       |           |    1     |
        # |   1   |     2       |  3 |              |    odd    |          |
        # |   1   |     3       |  4 |      2       |           |          |
        # |   1   |     4       |  5 |              |    odd    |          |
        # |   1   |     5       |  6 |      3       |           |          |
        # |   1   |     6       |  7 |              |    odd    |          |
        # |   1   |     7       |  8 |      4       |           |          |
        # |   1   |     8       |  9 |              |    odd    |          |
        # |   2   |     1       | 10 |      5       |           |    9     |
        # |   2   |     2       | 11 |              |    odd    |          |
        # |   2   |     3       | 12 |      6       |           |          |
        # |   2   |     4       | 13 |              |    odd    |          |
        # |   2   |     5       | 14 |      7       |           |          |
        # |   2   |     6       | 15 |              |    odd    |          |
        # |   2   |     7       | 16 |      8       |           |          |
        # |   2   |     8       | 17 |              |    odd    |          |
        # |   3   |     1       | 18 |      9       |           |   17     |
        # |   3   |     2       | 19 |              |    odd    |          |
        # |   3   |     3       | 20 |     10       |           |          |
        # |-------|-------------|----|--------------|-----------|----------|
        # |   3   |     4       | 21 |              | truncated |          |
        # |   3   |     5       | 22 |              | truncated |          |
        # |   3   |     6       | 23 |              | truncated |          |
        # |   3   |     7       | 24 |              | truncated |          |
        # |   3   |     8       | 25 |              | truncated |          |

        # With client-side filtering every other item, we'll need at least 19 items from the DB to produce a 10-item
        # page. If each DB query returns 9 items, that means 3 queries.
        self.assertEqual(
            [
                (
                    ('arg1', 'arg2'),
                    {
                        'kwarg1': 'baf',
                        'dynamo_pagination': {
                            'ExclusiveStartKey': {
                                'pk': '1'
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
                                'pk': '9',
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
                                'pk': '17',
                            },
                            'Limit': 10
                        }
                    }
                )
            ],
            calls
        )
        self.assertEqual(
            {

                # 3*8=24 items will have been returned from queries internally, but only 10 make it out to fill out the
                # pageSize
                'items': [UserRecordSchema().load(self._item)] * 10,
                'pagination': {
                    'pageSize': 10,
                    'lastKey': b64encode(
                        # Because we are mucking with pk for our filtering, the pk here should be the last value that
                        # passed through the client filter
                        json.dumps({'pk': '20'}).encode('utf-8')
                    ).decode('utf-8'),
                    'prevLastKey': last_key
                },
            },
            resp
        )

    def test_no_pagination_parameters(self):
        from data_model.query_paginator import paginated_query
        from data_model.schema.user import UserRecordSchema


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
                'items': [UserRecordSchema().load(self._item)],
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

        last_key = b64encode(json.dumps({'pk': 'USER#a4182428-d061-701c-82e5-a3d1d547d797'}).encode('utf-8'))
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
                                'pk': 'USER#a4182428-d061-701c-82e5-a3d1d547d797'
                            },
                            'Limit': 5
                        }
                    }
                )
            ],
            calls
        )

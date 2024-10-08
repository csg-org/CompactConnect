from aws_lambda_powertools import Logger

from config import config
from data_model.client import UserClient
from data_model.schema.user import UserAPISchema

logger = Logger()
user_client = UserClient(config=config)
user_api_schema = UserAPISchema()

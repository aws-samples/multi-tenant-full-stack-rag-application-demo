import pytest
import boto3
import json
import os
from multi_tenant_full_stack_rag_application.ingestion_provider.ingestion_status import IngestionStatus
from multi_tenant_full_stack_rag_application.ingestion_provider.ingestion_status_provider import IngestionStatusProvider
from multi_tenant_full_stack_rag_application.ingestion_provider.ingestion_status_provider_event import IngestionStatusProviderEvent
from multi_tenant_full_stack_rag_application.ingestion_provider.ingestion_status_provider_factory import IngestionStatusProviderFactory

from multi_tenant_full_stack_rag_application import utils

account = os.getenv('AWS_ACCOUNT_ID')
user_id = 'test_user_id'
doc_id = 'test_doc_id'
etag = 'test_etag'
lines_processed = 10
progress_status = 'IN_PROGRESS'

@pytest.fixture(scope="session")
def ingestion_status_provider():
    return IngestionStatusProviderFactory.get_ingestion_status_provider(
        ddb_client=utils.BotoClientProvider.get_client('dynamodb'),
    )

def test_create_ingestion_status(ingestion_status_provider):
    evt = {
        'operation': 'create_ingestion_status',
        'origin': utils.get_ssm_params('ingestion_status_provider_function_name'),
        "args": {
            'user_id': user_id,
            'doc_id': doc_id,
            'etag': etag,
            'lines_processed': lines_processed,
            'progress_status': progress_status,
            'delete_from_s3': True
        }
    }
    result = ingestion_status_provider.handler(
        evt, {}
    )
    print(f"test_create_ingestion_status got result: {result}")
    assert result['statusCode'] == '200'

def test_get_ingestion_status(ingestion_status_provider):
    evt = {
        'operation': 'get_ingestion_status',
        'origin': utils.get_ssm_params('ingestion_status_provider_function_name'),
        'args': {
            'user_id': user_id,
            'doc_id': doc_id
        }
    }
    result = ingestion_status_provider.handler(
        evt, {}
    )
    # print(f"test_get_ingestion_status got result: {result}")
    assert result['statusCode'] == '200'
    status = json.loads(result['body'])[0]
    assert status['user_id'] == user_id and \
        status['doc_id'] == doc_id and \
        status['etag'] == etag and \
        status['lines_processed'] == lines_processed and \
        status['progress_status'] == progress_status

def test_delete_ingestion_status(ingestion_status_provider):
    evt = {
        'operation': 'delete_ingestion_status',
        'origin': utils.get_ssm_params('ingestion_status_provider_function_name'),
        "args": {
            'user_id': user_id,
            'doc_id': doc_id,
            "delete_from_s3": True
        }
    }
    print(f"sending evt to delete: {evt}")
    result = ingestion_status_provider.handler(
        evt, {}
    )
    print(f"test_delete_ingestion_status got result: {result}")
    assert result['statusCode'] == '200'
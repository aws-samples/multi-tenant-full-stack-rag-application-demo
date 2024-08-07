import boto3
import json
import os
import pytest

from multi_tenant_full_stack_rag_application.auth_provider import AuthProviderFactory
from multi_tenant_full_stack_rag_application.document_collections_handler import DocumentCollection, DocumentCollectionsHandler, DocumentCollectionsHandlerEvent
from multi_tenant_full_stack_rag_application.ingestion_status_provider import IngestionStatusProviderFactory
from multi_tenant_full_stack_rag_application.system_settings_provider import SystemSettingsProviderFactory
from multi_tenant_full_stack_rag_application.user_settings_provider import UserSettingsProviderFactory
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_provider_factory import VectorStoreProviderFactory

region = os.getenv('AWS_REGION')

@pytest.fixture(scope="session")
def document_collections_handler():
    ap = CognitoAuthProvider(
            getenv('TEST_ACCOUNT'), 
            getenv('IDENTITY_POOL_ID'),
            getenv('USER_POOL_ID') ,
            getenv('AWS_REGION'),
    )
    isp = IngestionStatusProvider(ddb, ingestion_status_table)
    s3 = boto3.client('s3', region_name=region)
    ssm = boto3.client('ssm', region_name=region)
    ssp = SystemSettingsProviderFactory.get_system_settings_provider()
    usp = UserSettingsProviderFactory.get_user_settings_provider()
    vsp = VectorStoreProviderFactory.get_vector_store_provider(
        getenv('VECTOR_STORE_PROVIDER_PY_PATH'),
        json.loads(getenv('VECTOR_STORE_PROVIDER_ARGS'))
    )
    ddb = boto3.client('dynamodb', region_name=region)
    
    return DocumentCollectionsHandler(
        ap,
        isp,
        s3,
        ssm,
        ssp,
        usp,
        vsp
    )


@pytest.fixture(scope="session")
def user_settings_table():
    with open('../../frontend/backend_outputs.json', 'r') as r_in:
        resources = json.loads(r_in.read())
        print(f"Got resources {resources}")
        for key in resources:
            if 'UserSettingsTable' in key:
                for subkey in resources[key]:
                    if 'OutputRefUserSettingsTable' in subkey:
                        return resources[key][subkey]

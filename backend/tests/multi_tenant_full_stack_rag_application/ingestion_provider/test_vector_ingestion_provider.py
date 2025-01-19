import pytest
import boto3
import json
import os
import shutil
from multi_tenant_full_stack_rag_application.ingestion_provider.loaders.pdf_image_loader import PdfImageLoader
from multi_tenant_full_stack_rag_application.ingestion_provider.vector_ingestion_provider import VectorIngestionProvider
from multi_tenant_full_stack_rag_application.ingestion_provider.vector_ingestion_provider_event import VectorIngestionProviderEvent
from multi_tenant_full_stack_rag_application import utils

account = os.getenv('TEST_ACCOUNT')
user_id = os.getenv('CG_UID')
collection_id = os.getenv('COLL_ID')
if os.path.exists(f"/tmp/{collection_id}"):
    shutil.rmtree(f"/tmp/{collection_id}")
filename = 'redacted-Please_DocuSign_luna_full_cr.pdf'
local_dir = 'multi_tenant_full_stack_rag_application/ingestion_provider'
s3_key = f"private/{user_id}/{collection_id}/{filename}"
bucket = os.getenv('INGESTION_BUCKET')

@pytest.fixture
def vector_ingestion_provider(monkeypatch):
    s3 = boto3.client('s3')
    print(f"getcwd = {os.getcwd()}")
    s3.upload_file(f"{local_dir}/{filename}", bucket, s3_key)
    
    def mock_get_pdf_loader(self):
        template_path = '../src/multi_tenant_full_stack_rag_application/ingestion_provider/loaders/pdf_image_loader_ocr_template.txt'
        with open(template_path, 'r') as f:
            ocr_prompt = f.read()
            print(f'Initializing mock pdf loader with template text {ocr_prompt}')
            return PdfImageLoader(ocr_template_text=ocr_prompt)

    def mock_save_vector_docs(docs, collection_id, origin):
        return len(docs)

    monkeypatch.setattr(
        VectorIngestionProvider, 
        "get_pdf_loader", 
        mock_get_pdf_loader
    )
    
    vip = VectorIngestionProvider()
    monkeypatch.setattr(
        vip.utils,
        "save_vector_docs",
        mock_save_vector_docs
    )

    return vip


def test_handle_object_created(vector_ingestion_provider):
    ssm_client = utils.BotoClientProvider.get_client('ssm')
    print(f"vip pdf ocr text: {vector_ingestion_provider.pdf_loader.ocr_template_text}")
    # print(f"Got ssm_client {dir(ssm_client)}")
    # print(f"\n\nBefore creating vector ingestion provider, ssm parameters stored are: {ssm_client.describe_parameters(MaxResults=50)['Parameters']}\n\n")

    file_dict = {
        'account_id': os.getenv('TEST_ACCOUNT'),
        'user_id': user_id,
        'collection_id': collection_id,
        'filename': filename,
        'bucket': bucket,
        'etag': 'test_etag'
    }
    # with open('./multi_tenant_full_stack_rag_application/ingestion_provider/test_ocr_prompt.txt', 'r') as f_in:
    #     ocr_prompt = f_in.read()
    result = vector_ingestion_provider.handle_object_created(file_dict)
    assert len(result) == 1
    assert result[0].doc_id == f"{collection_id}/{filename}:0"


def dont_test_handler(vector_ingestion_provider):
    event = {
        'Records': [
            {
                'eventSource': 'aws:sqs',
                'receiptHandle': 'test_receipt_handle',
                'body': json.dumps({
                    'ingestion_files': [
                        {
                            'user_id': user_id,
                            'collection_id': collection_id,
                            'filename': filename,
                            'bucket': bucket,
                            'event_name': 'ObjectCreated:Put'
                        }
                    ]
                })
            }
        ]
    }
    result = vector_ingestion_provider.handler(event, {})
    assert result['status'] == 200
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import pytest
import boto3
import json
import os

from multi_tenant_full_stack_rag_application.document_collections_handler import DocumentCollection, DocumentCollectionsHandler
from multi_tenant_full_stack_rag_application import utils

user_id = os.getenv('CG_UID')
user_email = 'davetbo@amazon.com'
collection_name = "collection name"
collection_id = os.getenv('COLL_ID')
description = "collection description"

doc_collections_table_singleton = None

@pytest.fixture()
def doc_collections_table():
    global doc_collections_table_singleton
    if doc_collections_table_singleton is None:
        doc_collections_table_singleton = os.getenv('DOCUMENT_COLLECTIONS_TABLE')
    return doc_collections_table_singleton


#def doc_collections_handler(ddb_client, doc_collections_table, s3_client, ssm_client):
@pytest.fixture()
def doc_collections_handler():
    args = {
        "doc_collections_table":  os.getenv('DOCUMENT_COLLECTIONS_TABLE'),
        "ddb_client": utils.BotoClientProvider.get_client('dynamodb'),
        "lambda_client": utils.BotoClientProvider.get_client('lambda'),
        "s3_client": utils.BotoClientProvider.get_client('s3'),
        "ssm_client": utils.BotoClientProvider.get_client('ssm')
    }
    yield DocumentCollectionsHandler(**args)

@pytest.fixture()
def patch():
    def f(acct_id, jwt):
        # print(f"Got account_id {acct_id}, jwt {jwt}, but returning {user_id} as the patch")
        return user_id
    return(f)
        
def test_create_doc_collections_handler(doc_collections_handler):
    # assert doc_collections_handler.services['ingestion_status_provider'] == 'https://ingestion_status_provider'
    # ssert doc_collections_handler.services['vector_store_provider'] == 'https://vector_store_provider'
    assert isinstance(doc_collections_handler, DocumentCollectionsHandler)

def test_collections_to_dict(doc_collections_handler):
    args1 = {
        'user_id': user_id,
        'user_email': user_email,
        'collection_name': 'collection name',
        'description': 'collection description',
        'vector_db_type': 'mock',
        'collection_id': os.getenv('COLL_ID')
    }
    dc1 = DocumentCollection(**args1)
    assert dc1.user_id == args1['user_id']
    assert dc1.user_email == args1['user_email']
    assert dc1.collection_name == args1['collection_name']
    assert dc1.description == args1['description']
    assert dc1.vector_db_type == args1['vector_db_type']
    assert dc1.collection_id == args1['collection_id']

def test_create_get_doc_collections(doc_collections_handler):
    global collection_id

    # print("Running test_create_get_doc_collections")
    # print("\n\nFirst create a collection\n\n")
    event = {
        "headers": {
            "authorization": f"Bearer {os.getenv('JWT')}",
            "origin": "http://localhost:5173"
        },
        "requestContext": {
            "accountId": "redacted",
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": user_email
                    }
                }
            }
        },
        "routeKey": "POST /document_collections",
        "body": json.dumps({
            "document_collection": {
                "user_id": user_id,
                "user_email": user_email,
                "collection_name": collection_name,
                "description": description,
                "vector_db_type": "mock",
                "collection_id": None,
                "shared_with": []
            }
        })
    }

    # monkeypatch.setattr(
    #     doc_collections_handler.utils, 
    #     "get_userid_from_token",
    #     value=lambda x, y: patch(x, y)
    # )
    result = doc_collections_handler.handler(event, {})
    # print(f'test_create_get_doc_collections got create result {result}')
    doc_coll = json.loads(result['body'])[collection_name]
    
    assert result['statusCode'] == '200'
    # there's a filter to never send the user_id in a response. The user_id
    # in question is the Cognito Identity Pool Id, which is otherwise never
    # sent to the client, so it's good to use it for server-side
    # client identification that can't be guessed and is never sent to the client.
    assert 'user_id' not in doc_coll
    assert doc_coll['user_email'] == user_email
    assert doc_coll['collection_name'] == collection_name
    assert doc_coll['description'] == description
    assert doc_coll['collection_name'] == collection_name
    assert doc_coll['sort_key'] == f'collection::{collection_name}'
    
    # print("\n\nThen get back that collection\n\n")
    body = json.loads(result['body'])
    # print(f'got body {body}')
    # print(f'body keys: {body.keys()}')
    collection_id = body[collection_name]['collection_id']

    event = {
        "headers": {
            "authorization": f"Bearer {os.getenv('JWT')}",
            "origin": "http://localhost:5173"
        },
        "requestContext": {
            "accountId": "redacted",
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": user_email
                    }
                }
            }
        },
        "routeKey": "GET /document_collections",
        "pathParameters": {
            "collection_id": collection_id,
        }
    }
    result = doc_collections_handler.handler(event, {})
    # print(f'test_create_get_doc_collections got get result {result}')
    assert result['statusCode'] == '200'
    body = json.loads(result['body'])
    # print(f'got body {body}')
    rec = body['response'][collection_name]
    assert 'user_id' not in rec
    assert rec['collection_id'] == collection_id
    assert rec['sort_key'] == f'collection::{collection_name}'
    assert rec['user_email'] == user_email
    assert rec['description'] == description
    assert rec['shared_with'] == []
    assert rec['enrichment_pipelines'] == '{}'
    assert rec['graph_schema'] == '{}'

    # print("\n\nThen fetch all collections\n\n")

    event = {
        "headers": {
            "authorization": f"Bearer {os.getenv('JWT')}",
            "origin": "http://localhost:5173"
        },
        "requestContext": {
            "accountId": "redacted",
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": user_email
                    }
                }
            }
        },
        "routeKey": "GET /document_collections"
    }
    result = doc_collections_handler.handler(event, {})
    # print(f'test_create_get_doc_collections got get all result {result}')
    assert int(result['statusCode']) == 200
    assert collection_name in json.loads(result['body'])['response']

def test_delete_doc_collection(doc_collections_handler, monkeypatch, patch):
    event = {
        "headers": {
            "authorization": f"Bearer {os.getenv('JWT')}",
            "origin": "http://localhost:5173"
        },
        "requestContext": {
            "accountId": "redacted",
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": user_email
                    }
                }
            }
        },
        "routeKey": f"DELETE /document_collections/{collection_id}",
        "pathParameters": {
            "collection_id": collection_id
        }
    }
    result = doc_collections_handler.handler(event, {})
    # print(f'test_delete_doc_collection got delete result {result}')
    assert int(result['statusCode']) == 200
    assert json.loads(result['body'])['collection_id'] == collection_id 
    
def test_delete_file(doc_collections_handler):
    bucket = os.getenv('INGESTION_BUCKET')
    user_id = os.getenv('CG_UID')
    collection_id = os.getenv('COLL_ID')
    s3 = utils.BotoClientProvider.get_client('s3')
    with open('data.txt', 'w') as f_out:
        f_out.write('mock data')
    s3.upload_file(
        'data.txt', 
        bucket, 
        f"private/{user_id}/{collection_id}/data.txt"
    )
    event = {
        "headers": {
            "authorization": f"Bearer {os.getenv('JWT')}",
            "origin": "http://localhost:5173"
        },
        "requestContext": {
            "accountId": "redacted",
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": user_email
                    }
                }
            }
        },
        "routeKey": f"DELETE /document_collections/{collection_id}/data.txt",
        "pathParameters": {
            "collection_id": collection_id,
            "file_name": "data.txt"
        }
    }
    result = doc_collections_handler.handler(event, {})
    # print(f"delete file result: {result}")

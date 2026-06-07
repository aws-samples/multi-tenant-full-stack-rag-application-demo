#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import pytest
import boto3
import json
import os
import time

from multi_tenant_full_stack_rag_application.document_collections_handler import DocumentCollectionGraphSchema, DocumentCollectionsHandler
from multi_tenant_full_stack_rag_application import utils

user_id = os.getenv('CG_UID', 'test_user_123')
collection_name = "test_collection"
doc_collections_table_singleton = None

@pytest.fixture()
def doc_collections_table():
    global doc_collections_table_singleton
    if doc_collections_table_singleton is None:
        doc_collections_table_singleton = os.getenv('DOCUMENT_COLLECTIONS_TABLE', 'test_table')
    return doc_collections_table_singleton

@pytest.fixture()
def doc_collections_handler():
    args = {
        "doc_collections_table": os.getenv('DOCUMENT_COLLECTIONS_TABLE', 'test_table'),
        "ddb_client": utils.BotoClientProvider.get_client('dynamodb'),
        "lambda_client": utils.BotoClientProvider.get_client('lambda'),
        "s3_client": utils.BotoClientProvider.get_client('s3'),
        "ssm_client": utils.BotoClientProvider.get_client('ssm')
    }
    yield DocumentCollectionsHandler(**args)

def test_create_graph_schema_record():
    """Test creating a DocumentCollectionGraphSchema record"""
    test_schema = {
        "Person": {
            "node_properties": ["name", "age"],
            "edge_labels": ["knows", "works_with"]
        },
        "Company": {
            "node_properties": ["name", "industry"],
            "edge_labels": ["employs", "partners_with"]
        }
    }
    
    schema_record = DocumentCollectionGraphSchema(
        user_id=user_id,
        collection_name=collection_name,
        graph_schema=test_schema
    )
    
    assert schema_record.user_id == user_id
    assert schema_record.collection_name == collection_name
    assert schema_record.graph_schema == test_schema
    assert schema_record.sort_key.startswith(f"graph_schema::{collection_name}::")
    assert schema_record.timestamp_ms > 0

def test_graph_schema_to_ddb_record():
    """Test converting graph schema to DynamoDB record format"""
    test_schema = {
        "Person": {
            "node_properties": ["name", "age"],
            "edge_labels": ["knows"]
        }
    }
    
    schema_record = DocumentCollectionGraphSchema(
        user_id=user_id,
        collection_name=collection_name,
        graph_schema=test_schema
    )
    
    ddb_record = schema_record.to_ddb_record()
    
    assert ddb_record['partition_key']['S'] == user_id
    assert ddb_record['sort_key']['S'] == schema_record.sort_key
    assert ddb_record['collection_name']['S'] == collection_name
    assert json.loads(ddb_record['graph_schema']['S']) == test_schema
    assert 'timestamp_ms' in ddb_record

def test_graph_schema_from_ddb_record():
    """Test creating graph schema from DynamoDB record"""
    test_schema = {
        "Person": {
            "node_properties": ["name"],
            "edge_labels": ["knows"]
        }
    }
    
    timestamp_ms = int(time.time() * 1000)
    sort_key = f"graph_schema::{collection_name}::{timestamp_ms}"
    
    ddb_record = {
        'partition_key': {'S': user_id},
        'sort_key': {'S': sort_key},
        'collection_name': {'S': collection_name},
        'graph_schema': {'S': json.dumps(test_schema)},
        'timestamp_ms': {'N': str(timestamp_ms)}
    }
    
    schema_record = DocumentCollectionGraphSchema.from_ddb_record(ddb_record)
    
    assert schema_record.user_id == user_id
    assert schema_record.collection_name == collection_name
    assert schema_record.graph_schema == test_schema
    assert schema_record.timestamp_ms == timestamp_ms
    assert schema_record.sort_key == sort_key

def test_upsert_graph_schema(doc_collections_handler):
    """Test upserting a graph schema"""
    test_schema = {
        "Person": {
            "node_properties": ["name", "age"],
            "edge_labels": ["knows", "works_with"]
        }
    }
    
    # Test with real DynamoDB call
    schema_record = doc_collections_handler.upsert_graph_schema(
        user_id=user_id,
        collection_name=collection_name,
        graph_schema=test_schema
    )
    
    # Verify the returned record
    assert schema_record.user_id == user_id
    assert schema_record.collection_name == collection_name
    assert schema_record.graph_schema == test_schema
    assert schema_record.sort_key.startswith(f"graph_schema::{collection_name}::")
    assert schema_record.timestamp_ms > 0

def test_get_latest_graph_schema(doc_collections_handler):
    """Test getting the latest graph schema"""
    # First, create two schema records with different timestamps
    test_schema1 = {
        "Person": {
            "node_properties": ["name"],
            "edge_labels": ["knows"]
        }
    }
    
    test_schema2 = {
        "Person": {
            "node_properties": ["name", "age", "email"],
            "edge_labels": ["knows", "works_with"]
        },
        "Company": {
            "node_properties": ["name", "industry"],
            "edge_labels": ["employs"]
        }
    }
    
    # Insert first schema
    doc_collections_handler.upsert_graph_schema(
        user_id=user_id,
        collection_name=collection_name,
        graph_schema=test_schema1
    )
    
    # Wait a moment to ensure different timestamps
    time.sleep(0.1)
    
    # Insert second schema (which should be the latest)
    doc_collections_handler.upsert_graph_schema(
        user_id=user_id,
        collection_name=collection_name,
        graph_schema=test_schema2
    )
    
    # Get the latest schema
    latest_schema = doc_collections_handler.get_latest_graph_schema(
        user_id=user_id,
        collection_name=collection_name
    )
    
    # Verify we got the second schema (the latest one)
    assert latest_schema == test_schema2

def test_get_graph_schema_history(doc_collections_handler):
    """Test getting graph schema history"""
    # First, create three schema records with different timestamps
    test_schema1 = {"Person": {"node_properties": ["name"], "edge_labels": ["knows"]}}
    test_schema2 = {"Person": {"node_properties": ["name", "age"], "edge_labels": ["knows", "works_with"]}}
    test_schema3 = {"Person": {"node_properties": ["name", "age", "email"], "edge_labels": ["knows", "works_with", "reports_to"]}}
    
    # Clear any existing schemas for this test
    # This is a test-only operation to ensure clean state
    ddb = utils.BotoClientProvider.get_client('dynamodb')
    table_name = os.getenv('DOCUMENT_COLLECTIONS_TABLE', 'test_table')
    
    # Insert schemas with delays to ensure different timestamps
    schema1 = doc_collections_handler.upsert_graph_schema(
        user_id=user_id,
        collection_name=collection_name,
        graph_schema=test_schema1
    )
    time.sleep(0.1)
    
    schema2 = doc_collections_handler.upsert_graph_schema(
        user_id=user_id,
        collection_name=collection_name,
        graph_schema=test_schema2
    )
    time.sleep(0.1)
    
    schema3 = doc_collections_handler.upsert_graph_schema(
        user_id=user_id,
        collection_name=collection_name,
        graph_schema=test_schema3
    )
    
    # Get schema history with limit=2 (should get the 2 most recent)
    history = doc_collections_handler.get_graph_schema_history(
        user_id=user_id,
        collection_name=collection_name,
        limit=2
    )
    
    # Verify we got the expected number of records
    assert len(history) == 2
    
    # Verify they're in the right order (newest first)
    assert history[0].graph_schema == test_schema3
    assert history[1].graph_schema == test_schema2
    
    # Get all history
    all_history = doc_collections_handler.get_graph_schema_history(
        user_id=user_id,
        collection_name=collection_name,
        limit=10
    )
    
    # Verify we got at least 3 records
    assert len(all_history) >= 3
    
    # Verify the first three are in the right order
    assert all_history[0].graph_schema == test_schema3
    assert all_history[1].graph_schema == test_schema2
    assert all_history[2].graph_schema == test_schema1

def test_graph_schema_sort_key_format():
    """Test that sort keys are formatted correctly for proper sorting"""
    schema1 = DocumentCollectionGraphSchema(
        user_id=user_id,
        collection_name=collection_name,
        graph_schema={},
        timestamp_ms=1000000000000  # Earlier timestamp
    )
    
    time.sleep(0.001)  # Ensure different timestamp
    
    schema2 = DocumentCollectionGraphSchema(
        user_id=user_id,
        collection_name=collection_name,
        graph_schema={},
        timestamp_ms=1000000000001  # Later timestamp
    )
    
    # Both should have the same prefix
    prefix = f"graph_schema::{collection_name}::"
    assert schema1.sort_key.startswith(prefix)
    assert schema2.sort_key.startswith(prefix)
    
    # Later timestamp should sort after earlier timestamp lexicographically
    # (since DynamoDB sorts strings lexicographically)
    assert schema2.sort_key > schema1.sort_key

def test_graph_schema_equality():
    """Test graph schema equality comparison"""
    test_schema = {
        "Person": {
            "node_properties": ["name"],
            "edge_labels": ["knows"]
        }
    }
    
    timestamp_ms = int(time.time() * 1000)
    
    schema1 = DocumentCollectionGraphSchema(
        user_id=user_id,
        collection_name=collection_name,
        graph_schema=test_schema,
        timestamp_ms=timestamp_ms
    )
    
    schema2 = DocumentCollectionGraphSchema(
        user_id=user_id,
        collection_name=collection_name,
        graph_schema=test_schema,
        timestamp_ms=timestamp_ms
    )
    
    assert schema1 == schema2
    
    # Different timestamp should make them unequal
    schema3 = DocumentCollectionGraphSchema(
        user_id=user_id,
        collection_name=collection_name,
        graph_schema=test_schema,
        timestamp_ms=timestamp_ms + 1
    )
    
    assert schema1 != schema3

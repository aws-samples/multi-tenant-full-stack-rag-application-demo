#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import os
import pytest
from datetime import datetime
from multi_tenant_full_stack_rag_application.vector_store_provider.opensearch_vector_store_provider import OpenSearchVectorStoreProvider


@pytest.fixture
def vector_store_provider():
    vse = os.getenv('VECTOR_STORE_ENDPOINT')
    return OpenSearchVectorStoreProvider(vse)


def test_create_delete_index(vector_store_provider):
    index_name = f"index-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
    result = vector_store_provider.create_index(index_name)
    assert result == index_name

    result2 = vector_store_provider.delete_index(index_name)
    print(f"Result2 = {result2}")
    assert 1 == 2
    


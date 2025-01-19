import pytest
import boto3
import json
import os
import shutil
from multi_tenant_full_stack_rag_application.ingestion_provider.loaders.json_loader import JsonLoader


@pytest.fixture
def json_loader():
    return JsonLoader()


def test_json_loader_init(json_loader):
    assert isinstance(json_loader, JsonLoader)
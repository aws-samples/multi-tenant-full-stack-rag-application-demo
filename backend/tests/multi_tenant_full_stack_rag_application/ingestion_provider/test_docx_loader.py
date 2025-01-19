import pytest
import boto3
import json
import os
import shutil
from multi_tenant_full_stack_rag_application.ingestion_provider.loaders.docx_loader import DocxLoader
from multi_tenant_full_stack_rag_application.ingestion_provider.splitters.optimized_paragraph_splitter import OptimizedParagraphSplitter

@pytest.fixture
def docx_loader():
    return DocxLoader(splitter=OptimizedParagraphSplitter(max_tokens_per_chunk=7000))

def test_docx_loader_init(docx_loader):
    assert isinstance(docx_loader, DocxLoader)

def test_load_and_split(docx_loader):
    path = 'multi_tenant_full_stack_rag_application/ingestion_provider/FijiEvn_Consolidated_Country_Assessment_Report_Final_Draft_Sept28_09.docx'
    docs = docx_loader.load_and_split(path, os.getenv('CG_UID'))
    print(f"Got docs {docs}")
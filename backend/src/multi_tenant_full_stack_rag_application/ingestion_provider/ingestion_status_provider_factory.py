#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os
from importlib import import_module

from multi_tenant_full_stack_rag_application.utils import BotoClientProvider
from .ingestion_status_provider import IngestionStatusProvider


ingestion_status_provider_py_path = os.getenv('INGESTION_STATUS_PROVIDER_PY_PATH', 'multi_tenant_full_stack_rag_application.ingestion_provider.ingestion_status_provider.IngestionStatusProvider')

class IngestionStatusProviderFactory:
    @staticmethod
    def get_ingestion_status_provider(
        py_path=ingestion_status_provider_py_path,
        args=[],
        ddb_client=None,
        s3_client=None
    ) -> IngestionStatusProvider:
        if not ddb_client:
            ddb_client = BotoClientProvider.get_client('dynamodb')
  
        if not s3_client:
            s3_client = BotoClientProvider.get_client('s3')
            
        ingestion_status_table = os.getenv('INGESTION_STATUS_TABLE')

        if ingestion_status_table == '':
            raise Exception("You must set STACK_NAME in the environment variables so it can look up ingestion_status_table from Parameter Store.")
        
        ingestion_bucket = os.getenv('INGESTION_BUCKET')

        if args == []:
            args = [
                ddb_client,
                ingestion_bucket,
                ingestion_status_table,
                s3_client
            ]

        parts = py_path.split('.')
        ingestion_status_provider_file = '.'.join(parts[:-1])
        ingestion_status_provider_classname = parts[-1]
        ingestion_status_provider_module = import_module(ingestion_status_provider_file)
        ingestion_status_provider_class = getattr(ingestion_status_provider_module, ingestion_status_provider_classname)
        ingestion_status_provider: IngestionStatusProvider = \
            ingestion_status_provider_class(*args)
    
        return ingestion_status_provider
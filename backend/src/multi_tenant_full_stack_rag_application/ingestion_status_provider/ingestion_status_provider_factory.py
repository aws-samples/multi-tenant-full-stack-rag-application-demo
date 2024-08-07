#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os
from importlib import import_module

from multi_tenant_full_stack_rag_application.boto_client_provider import BotoClientProvider
from .ingestion_status_provider import IngestionStatusProvider

ddb_client = BotoClientProvider.get_client('dynamodb')

ingestion_status_provider_py_path = os.getenv('INGESTION_STATUS_PROVIDER_PY_PATH', 'multi_tenant_full_stack_rag_application.ingestion_status_provider.IngestionStatusProvider')
ingestion_status_table = os.getenv('INGESTION_STATUS_TABLE', '')
if ingestion_status_table == '':
    raise Exception('You must set the INGESTION_STATUS_TABLE environment variable. It should be injected automatically at deployment time, but if you\'re seeing this in dev, set that variable to something.')


class IngestionStatusProviderFactory:
    @staticmethod
    def get_ingestion_status_provider(
        py_path=ingestion_status_provider_py_path,
        args=[],
    ) -> IngestionStatusProvider:

        ingestion_status_table = os.getenv('INGESTION_STATUS_TABLE', '')
        if ingestion_status_table == '':
            raise Exception("You must set INGESTION_STATUS_TABLE in the environment variables.")
        
        if args == []:
            args = [
                BotoClientProvider.get_client('dynamodb'),
                ingestion_status_table
            ]

        parts = py_path.split('.')
        ingestion_status_provider_file = '.'.join(parts[:-1])
        ingestion_status_provider_classname = parts[-1]
        ingestion_status_provider_module = import_module(ingestion_status_provider_file)
        ingestion_status_provider_class = getattr(ingestion_status_provider_module, ingestion_status_provider_classname)
        ingestion_status_provider: IngestionStatusProvider = \
            ingestion_status_provider_class(*args)
    
        return ingestion_status_provider
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
import os
from importlib import import_module

from multi_tenant_full_stack_rag_application.boto_client_provider import BotoClientProvider
from multi_tenant_full_stack_rag_application.auth_provider import AuthProviderFactory
from multi_tenant_full_stack_rag_application.ingestion_status_provider import IngestionStatusProvider, IngestionStatusProviderFactory
from multi_tenant_full_stack_rag_application.system_settings_provider import SystemSettingsProvider, SystemSettingsProviderFactory
from multi_tenant_full_stack_rag_application.user_settings_provider import UserSettingsProviderFactory
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_provider_factory import VectorStoreProviderFactory   
from .document_collections_handler import DocumentCollectionsHandler


class DocumentCollectionsHandlerFactory: 
    @staticmethod
    def get_document_collections_handler(
        py_path: str='',
        args: [str]=[],
    ) -> DocumentCollectionsHandler:
        if py_path == '':
            py_path = os.getenv(
                'DOCUMENT_COLLECTIONS_HANDLER_PY_PATH',
                'multi_tenant_full_stack_rag_application.document_collections_handler.DocumentCollectionsHandler'
            )

        if args == []:
            args = [
                AuthProviderFactory.get_auth_provider(),
                IngestionStatusProviderFactory.get_ingestion_status_provider(),
                BotoClientProvider.get_client('s3'),
                BotoClientProvider.get_client('ssm'),
                SystemSettingsProviderFactory.get_system_settings_provider(),
                UserSettingsProviderFactory.get_user_settings_provider(),
                VectorStoreProviderFactory.get_vector_store_provider(),
            ]
        
        parts = py_path.split('.')
        provider_file = '.'.join(parts[:-1])
        provider_classname = parts[-1]
        provider_module = import_module(provider_file)
        provider_class = getattr(provider_module, provider_classname)
        provider: DocumentCollectionsHandler = provider_class(*args)
        return provider

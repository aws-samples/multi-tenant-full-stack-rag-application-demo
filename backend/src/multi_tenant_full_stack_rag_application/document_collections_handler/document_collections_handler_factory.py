#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
import os
from importlib import import_module

from multi_tenant_full_stack_rag_application.utils import BotoClientProvider
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
                os.getenv('DOCUMENT_COLLECTIONS_TABLE'),
                BotoClientProvider.get_client('cognito-identity'),
                BotoClientProvider.get_client('dynamodb'),
                BotoClientProvider.get_client('s3'),
                BotoClientProvider.get_client('ssm'),
            ]
        
        parts = py_path.split('.')
        provider_file = '.'.join(parts[:-1])
        provider_classname = parts[-1]
        provider_module = import_module(provider_file)
        provider_class = getattr(provider_module, provider_classname)
        provider: DocumentCollectionsHandler = provider_class(*args)
        return provider

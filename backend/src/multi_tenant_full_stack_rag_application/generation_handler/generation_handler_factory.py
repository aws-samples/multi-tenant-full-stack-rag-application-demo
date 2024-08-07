#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os
from importlib import import_module

from .generation_handler import GenerationHandler
from multi_tenant_full_stack_rag_application.auth_provider import AuthProviderFactory
from multi_tenant_full_stack_rag_application.bedrock_provider import BedrockProvider
from multi_tenant_full_stack_rag_application.boto_client_provider import BotoClientProvider
from multi_tenant_full_stack_rag_application.document_collections_handler import DocumentCollectionsHandlerFactory
from multi_tenant_full_stack_rag_application.prompt_template_handler import PromptTemplateHandlerFactory
from multi_tenant_full_stack_rag_application.user_settings_provider import UserSettingsProviderFactory
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_search_provider import VectorSearchProvider
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_provider import VectorStoreProvider
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_provider_factory import VectorStoreProviderFactory


class GenerationHandlerFactory:
    @staticmethod
    def get_generation_handler(
        py_path: str = '',
        args: [str] = [],
    ) -> GenerationHandler:
        if py_path == '':
            py_path = os.getenv(
                'GENERATION_HANDLER_PY_PATH',
                'multi_tenant_full_stack_rag_application.generation_handler.GenerationHandler'
            )
        if args == []:
            args = [
                AuthProviderFactory.get_auth_provider(),
                BedrockProvider(
                    BotoClientProvider.get_client('bedrock'),
                    BotoClientProvider.get_client('bedrock-agent'),
                    BotoClientProvider.get_client('bedrock-agent-runtime'),
                    BotoClientProvider.get_client('bedrock-runtime')
                ),
                DocumentCollectionsHandlerFactory.get_document_collections_handler(),
                os.getenv('NEPTUNE_ENDPOINT'),
                PromptTemplateHandlerFactory.get_prompt_template_handler(),
                BotoClientProvider.get_client('ssm'),
                VectorSearchProvider(
                    DocumentCollectionsHandlerFactory.get_document_collections_handler(),
                    UserSettingsProviderFactory.get_user_settings_provider(),
                    VectorStoreProviderFactory.get_vector_store_provider()
                )
            ]
        parts = py_path.split('.')
        handler_file = '.'.join(parts[:-1])
        handler_classname = parts[-1]
        handler_module = import_module(handler_file)
        handler_class = getattr(handler_module, handler_classname)
        handler: GenerationHandler = handler_class(*args)
        return handler
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os
from importlib import import_module

from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_provider import VectorStoreProvider


class VectorStoreProviderFactory:
    @staticmethod
    def get_vector_store_provider(
        py_path: str='',
        args={}
    ):
        if "vector_store_endpoint" not in args:
            args["vector_store_endpoint"] = os.getenv('VECTOR_STORE_ENDPOINT', '')
        # # print(f'Vector Store Provider Args: {args}')
        if py_path == '':
            py_path = os.getenv('VECTOR_STORE_PROVIDER_PY_PATH', '')
        if py_path == '':
            raise Exception('You must set VECTOR_STORE_PROVIDER_PY_PATH in the environment or pass it in.')
        parts = py_path.split('.')
        provider_file = '.'.join(parts[:-1])
        provider_classname = parts[-1]
        provider_module = import_module(provider_file)
        provider_class = getattr(provider_module, provider_classname)
        provider: VectorStoreProvider = provider_class(**args)
        return provider


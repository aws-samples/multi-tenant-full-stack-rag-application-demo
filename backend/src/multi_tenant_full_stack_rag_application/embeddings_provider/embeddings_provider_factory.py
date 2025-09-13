#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os
from importlib import import_module

from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider import EmbeddingsProvider

class EmbeddingsProviderFactory:
    @staticmethod
    def get_embeddings_provider(
        py_path='',
        args=[],
    ) -> EmbeddingsProvider:
        if py_path == '':
            py_path = os.getenv('EMBEDDINGS_PROVIDER_PY_PATH', '')
        if py_path == '':
            raise Exception('You must set EMBEDDINGS_PROVIDER_PY_PATH in the environment or pass it in.')
        if args == []:
            args = json.loads(os.getenv('EMBEDDINGS_PROVIDER_ARGS', '[]'))
            if isinstance(args, dict):
                args = args.values()
        print(f"Got py_path {py_path} embeddings_provider_args {args}")
        # # print(f"EmbeddingsProviderFactory loading provider {py_path} with args {args}")
        parts = py_path.split('.')
        provider_file = '.'.join(parts[:-1])
        provider_classname = parts[-1]
        provider_module = import_module(provider_file)
        provider_class = getattr(provider_module, provider_classname)
        provider: EmbeddingsProvider =provider_class(*args)
        return provider
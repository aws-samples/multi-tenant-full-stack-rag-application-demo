#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os
from importlib import import_module

from .generation_handler import GenerationHandler
from multi_tenant_full_stack_rag_application.utils import BotoClientProvider

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
        parts = py_path.split('.')
        handler_file = '.'.join(parts[:-1])
        handler_classname = parts[-1]
        handler_module = import_module(handler_file)
        handler_class = getattr(handler_module, handler_classname)
        handler: GenerationHandler = handler_class(*args)
        return handler
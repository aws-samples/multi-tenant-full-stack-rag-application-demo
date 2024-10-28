#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os
from importlib import import_module

from multi_tenant_full_stack_rag_application import utils 
from .prompt_template_handler import PromptTemplateHandler

class PromptTemplateHandlerFactory:
    @staticmethod
    def get_prompt_template_handler(
        py_path: str = '',
        args: [str] = [],
    ) -> PromptTemplateHandler:
        if py_path == '':
            py_path = os.getenv(
                'PROMPT_TEMPLATE_HANDLER_PY_PATH',
                'multi_tenant_full_stack_rag_application.prompt_template_handler.PromptTemplateHandler',
            )
        if args == []:
            args = [
                utils.BotoClientProvider.get_client('ssm'),
            ]
        parts = py_path.split('.')
        handler_file = '.'.join(parts[:-1])
        handler_classname = parts[-1]
        handler_module = import_module(handler_file)
        handler_class = getattr(handler_module, handler_classname)
        handler: PromptTemplateHandler = handler_class(*args)
        return handler
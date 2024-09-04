#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os
from importlib import import_module

from multi_tenant_full_stack_rag_application.utils import BotoClientProvider
from .auth_provider import AuthProvider

class AuthProviderFactory: 
    @staticmethod
    def get_auth_provider() -> AuthProvider:
        ssm = BotoClientProvider.get_client('ssm')
        auth_provider_args =  json.loads(ssm.get_parameter(
            Name=f'/{os.getenv("STACK_NAME")}/auth_provider_args'
        )['Parameter']['Value'])  
        auth_provider_py_path = ssm.get_parameter(
            Name=f'/{os.getenv("STACK_NAME")}/auth_provider_py_path'
        )['Parameter']['Value']
        print(f"AuthProviderFactory: auth_provider_args={auth_provider_args}")
        parts = auth_provider_py_path.split('.')
        provider_file = '.'.join(parts[:-1])
        provider_classname = parts[-1]
        provider_module = import_module(provider_file)
        provider_class = getattr(provider_module, provider_classname)
        provider: AuthProvider = provider_class(*auth_provider_args)
        return provider

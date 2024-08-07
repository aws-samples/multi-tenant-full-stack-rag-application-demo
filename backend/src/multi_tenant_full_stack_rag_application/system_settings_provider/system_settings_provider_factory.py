#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
import os
from importlib import import_module

from multi_tenant_full_stack_rag_application.boto_client_provider import BotoClientProvider
from .system_settings_provider import SystemSettingsProvider


class SystemSettingsProviderFactory: 
    @staticmethod
    def get_system_settings_provider(
        py_path: str='',
        args: [str]=[],
    ) -> SystemSettingsProvider:
        system_settings_table = os.getenv('SYSTEM_SETTINGS_TABLE', '')
        if system_settings_table == '':
            raise Exception('You must set the SYSTEM_SETTINGS_TABLE variable. It should be injected into the stack at deployment time. If you\'re seeing this in dev, set that variable.')
        
        if py_path == '': 
            py_path = os.getenv('SYSTEM_SETTINGS_PROVIDER_PY_PATH', 'multi_tenant_full_stack_rag_application.system_settings_provider.SystemSettingsProvider')
        if args == []:
            args = [
                BotoClientProvider.get_client('dynamodb'),
                system_settings_table
            ]
        
        parts = py_path.split('.')
        system_settings_provider_file = '.'.join(parts[:-1])
        system_settings_provider_classname = parts[-1]
        system_settings_provider_module = import_module(system_settings_provider_file)
        system_settings_provider_class = getattr(system_settings_provider_module, system_settings_provider_classname)
        system_settings_provider: SystemSettingsProvider = system_settings_provider_class(*args)
        return system_settings_provider
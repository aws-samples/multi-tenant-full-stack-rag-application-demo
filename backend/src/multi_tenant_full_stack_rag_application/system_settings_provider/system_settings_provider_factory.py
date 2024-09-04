#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
import os
from importlib import import_module

from multi_tenant_full_stack_rag_application.utils import BotoClientProvider
from .system_settings_provider import SystemSettingsProvider


ssm = None
ddb = None

class SystemSettingsProviderFactory: 
    @staticmethod
    def get_system_settings_provider(
        py_path: str='',
        args: [str]=[],
        *,
        ddb_client: boto3.client=None,
        ssm_client: boto3.client=None
    ) -> SystemSettingsProvider:
        global ddb, ssm

        if not ddb_client:
            ddb = BotoClientProvider.get_client('dynamodb')
        else:
            print("Using provided ddb_client")
            ddb = ddb_client

        if not ssm_client:
            ssm = BotoClientProvider.get_client('ssm')
        else:
            ssm = ssm_client

        ssm_param_name = f'/{os.getenv("STACK_NAME")}/system_settings_table'
        system_settings_table = ssm.get_parameter(
            Name=ssm_param_name
        )['Parameter']['Value']

        if system_settings_table == '':
            raise Exception(f'Could not find {ssm_param_name} in parameter store')
        
        if py_path == '': 
            py_path = os.getenv('SYSTEM_SETTINGS_PROVIDER_PY_PATH', 'multi_tenant_full_stack_rag_application.system_settings_provider.SystemSettingsProvider')
        if args == []:
            args = [
                ddb,
                system_settings_table
            ]
        
        parts = py_path.split('.')
        system_settings_provider_file = '.'.join(parts[:-1])
        system_settings_provider_classname = parts[-1]
        system_settings_provider_module = import_module(system_settings_provider_file)
        system_settings_provider_class = getattr(system_settings_provider_module, system_settings_provider_classname)
        system_settings_provider: SystemSettingsProvider = system_settings_provider_class(*args)
        return system_settings_provider
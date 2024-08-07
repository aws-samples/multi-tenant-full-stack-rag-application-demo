#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
import os
from importlib import import_module

from multi_tenant_full_stack_rag_application.boto_client_provider import BotoClientProvider
from .user_settings_provider import UserSettingsProvider


class UserSettingsProviderFactory: 
    @staticmethod
    def get_user_settings_provider(
        py_path: str='',
        args: [str]=[],
    ) -> UserSettingsProvider:
        user_settings_table = os.getenv('USER_SETTINGS_TABLE', '')
        if user_settings_table == '':
            raise Exception('You must set the USER_SETTINGS_TABLE variable. It should be injected into the stack at deployment time. If you\'re seeing this in dev, set that variable.')
        
        if py_path == '': 
            py_path = os.getenv('USER_SETTINGS_PROVIDER_PY_PATH', 'multi_tenant_full_stack_rag_application.user_settings_provider.UserSettingsProvider')
        if args == []:
            args = [
                BotoClientProvider.get_client('dynamodb'),
                user_settings_table
            ]
        
        parts = py_path.split('.')
        user_settings_provider_file = '.'.join(parts[:-1])
        user_settings_provider_classname = parts[-1]
        user_settings_provider_module = import_module(user_settings_provider_file)
        user_settings_provider_class = getattr(user_settings_provider_module, user_settings_provider_classname)
        user_settings_provider: UserSettingsProvider = user_settings_provider_class(*args)
        return user_settings_provider
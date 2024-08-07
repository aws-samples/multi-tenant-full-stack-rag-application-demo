#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3

from multi_tenant_full_stack_rag_application.system_settings_provider import SystemSetting, SystemSettingsProvider, SystemSettingsProviderFactory

system_settings_provider = None

def handler(event, context):
    global system_settings_provider
    print(f"post_confirmation_hook.handler got event {event}")
    email = event['request']['userAttributes']['email']
    if not system_settings_provider:
        system_settings_provider = SystemSettingsProviderFactory.get_system_settings_provider()

    response = system_settings_provider.set_system_setting(
        SystemSetting(
            'user_by_email',
            email
        )
    )
    print(f"Got response {response}")
    return event
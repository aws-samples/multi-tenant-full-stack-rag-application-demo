#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import requests

from datetime import datetime

from multi_tenant_full_stack_rag_application.auth_provider import AuthProvider, AuthProviderFactory
from multi_tenant_full_stack_rag_application.system_settings_provider import SystemSettingsProvider, SystemSettingsProviderFactory
from multi_tenant_full_stack_rag_application.utils import format_response
from .initialization_handler_event import InitializationHandlerEvent


auth_provider = None
initialization_handler = None
system_settings_provider = None


max_init_frequency_s = 30 # in seconds, default to 5 minutes at prod
last_init = 0


class InitializationHandler:
    def __init__(self,
        system_settings_provider: SystemSettingsProvider,
        urls_to_init: [str],
    ):
        self.auth_provider = auth_provider
        self.init_urls = urls_to_init 
        self.system_settings_provider = system_settings_provider       

    def initialize(self, handler_evt):
        user_rec = self.system_settings_provider.get_system_settings('user_by_email', handler_evt.user_email)[0]
        print(f"Got user record {user_rec}")
        user_rec.data['user_id'] = handler_evt.user_id
        self.system_settings_provider.set_system_setting(user_rec)
        print(f"Initialized urls {handler_evt.urls_to_init} and updated user record {user_rec}")
        for url in handler_evt.urls_to_init:
            print(f"Calling {url}")
            requests.get(url, timeout=60)
        return "success"

def handler(event, context):
    global auth_provider, initialization_handler, last_init, system_settings_provider
    print(f"initialization_handler.handler received event {event}")
    handler_evt = InitializationHandlerEvent().from_lambda_event(event)
    print(f"converted event to InitializationHandlerEvent: {handler_evt}")
    now = datetime.now().timestamp()
    status = 200
    user_id = None
    if handler_evt.method == 'OPTIONS':
        result = {}
    
    auth_provider =  AuthProviderFactory.get_auth_provider()

    if hasattr(handler_evt, "auth_token") and handler_evt.auth_token is not None:
        user_id = auth_provider.get_userid_from_token(handler_evt.auth_token)
        handler_evt.user_id = user_id

    if handler_evt.method == "POST" and handler_evt.path == "/initialization":
        # if it's been less than max_init_frequency, 
        # just return
        print(f"It's now {now} and we last ran {now - last_init} seconds ago. Is it less than {max_init_frequency_s}?")
        if now - last_init < max_init_frequency_s:
            print("Yes, it is less than {max_init_frequency_s} seconds. Returning")
            result = f"Initialization recently done within the last {max_init_frequency_s} seconds", handler_evt.origin
        else:
            print("No, it is more than {max_init_frequency_s} seconds. Updating last_init.")
            last_init = now

            if not initialization_handler:
                system_settings_provider = SystemSettingsProviderFactory.get_system_settings_provider()
                initialization_handler = InitializationHandler(
                    system_settings_provider,
                    handler_evt.urls_to_init
                )

            print(f"Calling initialization_handler with urls {handler_evt.urls_to_init}")
            result = initialization_handler.initialize(handler_evt)

    return format_response(200, result, handler_evt.origin)

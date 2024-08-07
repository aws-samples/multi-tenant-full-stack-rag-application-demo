#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os
import sys
import boto3 
from datetime import datetime
from uuid import uuid4

from multi_tenant_full_stack_rag_application.auth_provider import AuthProvider, AuthProviderFactory
from multi_tenant_full_stack_rag_application.boto_client_provider import BotoClientProvider
from .prompt_template_handler_event import PromptTemplateHandlerEvent
from .prompt_template import PromptTemplate
from multi_tenant_full_stack_rag_application.user_settings_provider import UserSetting, UserSettingsProvider, UserSettingsProviderFactory
from multi_tenant_full_stack_rag_application.utils import format_response

"""
GET /prompt_templates: list prompt templates
POST /prompt_templates: create or update prompt template
    body = {
        'template_name': str,
        'template_text': str,
        'model_ids': [str],
        'template_id'?: str
    }
DELETE /prompt_templates/{prompt_template_id} :  delete a prompt template
"""

# use global variables to store injected dependencies on the first initialization
initialized = None
auth_provider = None
user_settings_provider = None
ssm = None
prompt_template_handler = None


class PromptTemplateHandler:
    def __init__(self,
        auth_provider: AuthProvider,
        ssm_client: boto3.client,
        user_settings_provider: UserSettingsProvider,
        bedrock_model_param_path:str = 'multi_tenant_full_stack_rag_application/bedrock_provider/bedrock_model_params.json',
        prompt_template_path:str = 'multi_tenant_full_stack_rag_application/prompt_template_handler/prompt_templates'
    ):
        self.prompt_template_path = prompt_template_path
        self.ssm_client = ssm_client
        self.user_id = None
        self.auth_provider = auth_provider
        self.user_settings_provider = user_settings_provider
        origin_domain_name = ssm_client.get_parameter(
            Name='/multitenantrag/frontendOrigin'
        )['Parameter']['Value']
        self.frontend_origins = [
            f'https://{origin_domain_name}',
            'http://localhost:5173'
        ]
        template_files = os.listdir(prompt_template_path)
        # print(f"Template files in {prompt_template_path}: {template_files}")
        self.default_templates = {}
        with open(bedrock_model_param_path, 'r') as f:
           self.bedrock_model_params = json.loads(f.read())

        for filename in template_files:
            # print(f"Loading template file {filename}")
            template_name = filename.replace('.txt', '')
            model_ids = self.get_default_template_model_ids(template_name)
            # print(f"Model ids for template {template_name} {model_ids}")
            # print(f"Loading template file from {prompt_template_path}/{filename}")
            with open(f'{prompt_template_path}/{filename}', 'r') as f:
                self.default_templates[template_name] = PromptTemplate(
                    user_id=None,
                    template_name=template_name,
                    template_text=f.read(),
                    model_ids=model_ids,
                    template_id=template_name,
                )
                # print(f"Got prompt template: {self.default_templates[template_name]}")

    @staticmethod
    def create_prompt_template_record(template_dict):
        template_id = uuid4().hex if 'template_id' not in template_dict \
            else template_dict['template_id']
        created = datetime.now().isoformat() + 'Z' if 'created_date' \
            not in template_dict else template_dict['created_date']
        updated = created if 'updated_date' not in template_dict else \
            template_dict['updated_date']
        if 'stop_sequences' not in template_dict:
            template_dict['stop_sequences'] = []
        updated = created
        stop_seqs = [] if not 'stop_sequences' in template_dict else \
            template_dict['stop_sequences']
        return PromptTemplate(
            template_dict['user_id'],
            template_dict['template_name'],
            template_dict['template_text'],
            template_dict['model_ids'],
            stop_seqs,
            template_id,
            created,
            updated
        )

    def delete_prompt_template(self, user_id, template_id):
        curr_templates = self.get_prompt_templates(user_id)
        final_templates = {}
        
        for template_name in curr_templates:
            template = curr_templates[template_name]
            if template.template_id != template_id:
                if hasattr(template,'stop_sequences') and \
                    (
                        not isinstance(template.stop_sequences, list) or \
                        len(template.stop_sequences) == 0
                    ):
                    delattr(template,'stop_sequences')

                final_templates[template_name] = template
        
        user_setting = UserSetting(
            user_id, 
            'prompt_templates', 
            self.templates_to_dict(final_templates)
        )
        print(f"Setting data: {user_setting} ")
        self.user_settings_provider.set_user_setting(user_setting)
        return final_templates

    def get_default_template_model_ids(self, template_name):
        search_str = template_name.split('_')[1]
        model_ids = []
        for model_id in self.bedrock_model_params:
            if search_str in model_id:
                model_ids.append(model_id)
        return model_ids

    def get_prompt_template(self, user_id, template_id) -> PromptTemplate:
        print(f"Getting prompt template {template_id} for user {user_id}")
        templates = self.get_prompt_templates(user_id)
        template = None
        for template_name in templates:
            tmp = templates[template_name]
            if tmp.template_id == template_id:
                template = tmp
                break
        return template

    def get_prompt_templates(self, user_id):
        user_setting = self.user_settings_provider.get_user_setting(user_id, 'prompt_templates')
        template_data = {} if not hasattr(user_setting, 'data') else user_setting.data
        templates = {}
        for template_name in template_data:
            sub = template_data[template_name]
            stop_seqs = []
            if 'stop_sequences' in sub:
                stop_seqs = sub['stop_sequences']
            print(f"Got sub {sub}")
            if not 'model_ids' in sub:
                sub['model_ids'] = []
            template_obj = PromptTemplate(
                user_id,
                template_name,
                sub['template_text'],
                sub['model_ids'],
                stop_seqs,
                sub['template_id'],
                sub['created_date'],
                sub['updated_date']
            )
            templates[template_name] = template_obj
        for template_name in self.default_templates:
            if template_name not in template_data:
                template_obj = PromptTemplate(
                    user_id,
                    template_name,
                    self.default_templates[template_name].template_text,
                    self.get_default_template_model_ids(template_name),
                    [],
                    template_name,
                    None,
                    None
                )
                templates[template_name] = template_obj
        print(f"get_prompt_templates returning {templates}")
        return templates

    def handler(self, event, context): 
        print(f"Got event {event}")
        
        handler_evt = PromptTemplateHandlerEvent().from_lambda_event(event)
        method = handler_evt.method
        path = handler_evt.path

        if handler_evt.origin not in self.frontend_origins:
            return format_response(403, {}, None)
        
        user_id = None
        status = 200
        if hasattr(handler_evt, 'auth_token') and handler_evt.auth_token is not None:
            user_id = self.auth_provider.get_userid_from_token(handler_evt.auth_token)
        
        if method != 'OPTIONS' and user_id == None:
            status = 403
            result = {"error": "forbidden"}
        
        elif method == 'OPTIONS':
            result = {}

        elif method == 'GET' and path == '/prompt_templates':
            templates = self.get_prompt_templates(user_id)
            result = self.templates_to_dict(templates)

        elif method == 'GET' and path.startswith('/prompt_templates/'):
            template_id = path.split('?')[0]
            template = self.get_prompt_template(user_id, template_id)
            result = self.templates_to_dict({template.template_name: template})

        elif method == 'POST' and path == '/prompt_templates':
            body = json.loads(event['body'])
            # add the user_id to the prompt template before passing it on.
            body['prompt_template']['user_id'] = user_id
            new_template_record = self.create_prompt_template_record(body['prompt_template'])
            updated_templates = self.update_prompt_templates(new_template_record)
            result = self.templates_to_dict(updated_templates)

        elif method == 'DELETE' and path == ('/prompt_templates'):
            template = json.loads(event['body'])['prompt_template']
            template_id = template['template_id']
            updated_templates = self.delete_prompt_template(user_id, template_id)
            result = self.templates_to_dict(updated_templates)
            
        print(f"Returning result {result}")  
        return format_response(status, result, handler_evt.origin)

    @staticmethod
    def templates_to_dict(templates):
        print(f"templates_to_dict got templates {templates}")
        final_templates= {}
        for template_name in templates:
            template = templates[template_name]
            if isinstance(template, PromptTemplate):
                template = template.__dict__()

            print(f"Template is now {template}, type {type(template)}")
            template_name = template['template_name']
            del template['user_id']
            del template['template_name']
            if template['stop_sequences'] == []:
                del template['stop_sequences']
            final_templates[template_name] = template
        return final_templates

    def update_prompt_templates(self, new_template: PromptTemplate):
        print(f"update_prompt_templates got new prompt template {new_template}")
        new_template_rec = new_template.to_ddb_record()
        templates = self.get_prompt_templates(new_template.user_id)
        final_templates = {}
        found = False

        for template_name in templates:
            if template_name.startswith('default_'):
                continue
            template = templates[template_name]
            
            if template.template_id == new_template.template_id:
                final_templates[template_name] = new_template
                found = True
            else: 
                final_templates[template_name] = template
        if not found and not new_template.template_name.startswith('default_'):
            final_templates[new_template.template_name] = new_template

        user_setting_data = {}
        for template_name in final_templates:
            template = final_templates[template_name]
            print(f"Updating prompt templates. templates is now {template}")
            if isinstance(template, PromptTemplate):
                template = template.__dict__()
            del template['user_id']
            if template['stop_sequences'] == []:
                del template['stop_sequences']
            user_setting_data[template_name] = template
        print(f'Creating user_setting {user_setting_data} from {new_template}')
        result = self.user_settings_provider.set_user_setting(
            UserSetting(
                new_template.user_id,
                'prompt_templates',
                user_setting_data
            )
        )
        return final_templates

def handler(event, context):
    global initialized, auth_provider, user_settings_provider, ssm, prompt_template_handler
    if not initialized:
        auth_provider = AuthProviderFactory.get_auth_provider()
        user_settings_provider = UserSettingsProviderFactory.get_user_settings_provider()
        ssm = BotoClientProvider.get_client('ssm')
        prompt_template_handler = PromptTemplateHandler(
            auth_provider, ssm, user_settings_provider
        )
        initialized = True
    return prompt_template_handler.handler(event, context)

if __name__=='__main__':
    with open ('event.json', 'r') as evt_in:
        evt = json.loads(evt_in.read())
        PromptTemplateHandler.handler(evt, {})

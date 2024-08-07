import boto3
import json
import os

from multi_tenant_full_stack_rag_application.auth_provider import AuthProvider, AuthProviderFactory
from multi_tenant_full_stack_rag_application.boto_client_provider import BotoClientProvider
from multi_tenant_full_stack_rag_application.enrichment_pipelines import EnrichmentPipelinesHandlerEvent
from multi_tenant_full_stack_rag_application.utils import format_response

auth_provider = None
initialized = False
enabled_pipelines_param_name = None
enrichment_pipelines_handler = None
ssm_client = None


class EnrichmentPipelinesHandler: 
    def __init__(self, 
        auth_provider: AuthProvider,
        ssm_client
    ):
        self.auth_provider = auth_provider
        origin_domain_name = ssm_client.get_parameter(
            Name='/multitenantrag/frontendOrigin'
        )['Parameter']['Value']
        self.frontend_origins = [
            f'https://{origin_domain_name}',
            'http://localhost:5173'
        ]
        enabled_pipelines = ssm_client.get_parameter(Name=enabled_pipelines_param_name)['Parameter']['Value']
        if enabled_pipelines:
            enabled_pipelines = json.loads(enabled_pipelines)
            self.enabled_pipelines = enabled_pipelines
        else:
            raise Exception("Couldn't load enabled pipelines.")
        
    def handler(self, handler_evt):
        if handler_evt.origin not in self.frontend_origins:
            return format_response(403, {}, None)
        status = 200
        user_id = None

        if handler_evt.method == 'OPTIONS':
            result = {}

        if hasattr(handler_evt, 'auth_token') and handler_evt.auth_token is not None:
            user_id = self.auth_provider.get_userid_from_token(handler_evt.auth_token)
            handler_evt.user_id = user_id
        
        if handler_evt.method == 'GET' and handler_evt.path == '/enrichment_pipelines':
            result = self.enabled_pipelines
        
        return format_response(status, result, handler_evt.origin)


def handler(event, context):
    global auth_provider, enabled_pipelines_param_name, enrichment_pipelines_handler, initialized, ssm_client
    print(f"enrichment_pipelines received event {event}")

    if not initialized:
        auth_provider = AuthProviderFactory.get_auth_provider()
        ssm_client = BotoClientProvider.get_client('ssm')
        enabled_pipelines_param_name = os.getenv('ENRICHMENT_PIPELINES_SSM_PARAM_NAME')
        enrichment_pipelines_handler = EnrichmentPipelinesHandler(auth_provider, ssm_client)
        initialized = True
    handler_evt = EnrichmentPipelinesHandlerEvent().from_lambda_event(event)
    return enrichment_pipelines_handler.handler(handler_evt)

    
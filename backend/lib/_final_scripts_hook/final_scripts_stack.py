from aws_cdk import (
    NestedStack,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_opensearchservice as aos,
    aws_s3 as s3,
    aws_sqs as sqs,
)

from constructs import Construct

from lib.shared.opensearch_access_policy import OpenSearchAccessPolicy
# from lib.shared.bucket_to_queue_event_trigger import BucketToQueueNotification
# from lib.shared.queue_to_function_event_trigger import QueueToFunctionTrigger


class FinalScriptsStack(NestedStack):
    def __init__(self, scope: Construct, construct_id: str, 
        bedrock_provider_function: lambda_.IFunction,
        doc_collections_handler_function: lambda_.IFunction,
        domain: aos.Domain,
        embeddings_provider_function: lambda_.IFunction,
        extraction_principal: iam.IPrincipal,
        graph_store_provider_function: lambda_.IFunction,
        inference_principal: iam.IPrincipal,
        ingestion_bucket: s3.IBucket,
        ingestion_function: lambda_.IFunction,
        # ingestion_principal: iam.IPrincipal,
        ingestion_queue: sqs.IQueue,
        ingestion_status_provider_function: lambda_.IFunction,
        prompt_templates_handler_function: lambda_.IFunction,
        vector_store_provider_function: lambda_.IFunction,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ingestion_principal = ingestion_function.grant_principal
        vector_store_principal = vector_store_provider_function.grant_principal

        OpenSearchAccessPolicy(self, "OpenSearchIngestionAccessPolicy",
            domain=domain,
            grantee_principal=ingestion_principal,
            domain_read_access=True,
            domain_write_access=True,
            index_read_access=True,
            index_write_access=True
        )

        # self.bucket_to_queue_trigger = BucketToQueueNotification(self, 'IngestionBucketNotifications',
        #     bucket_name=ingestion_bucket.bucket_name,
        #     queue=ingestion_queue,
        #     resource_name='IngestionBucketToQueueTrigger'
        # )

        # self.queue_to_function_trigger_stack = QueueToFunctionTrigger(self, 'QueueToFunctionTrigger',
        #     function=ingestion_function,
        #     queue_arn=ingestion_queue.queue_arn,
        #     resource_name='IngestionQueueToFunctionTrigger'
        # )
        
        OpenSearchAccessPolicy(self, "OpenSearchInferenceAccessPolicy",
            domain=domain,
            grantee_principal=inference_principal,
            domain_read_access=False,
            domain_write_access=False,
            index_read_access=True,
            index_write_access=False
        )
        
        bedrock_provider_function.grant_invoke(embeddings_provider_function.grant_principal)

        bedrock_provider_function.grant_invoke(extraction_principal)
        graph_store_provider_function.grant_invoke(extraction_principal)
        ingestion_status_provider_function.grant_invoke(extraction_principal)
        vector_store_provider_function.grant_invoke(extraction_principal)
    
        bedrock_provider_function.grant_invoke(inference_principal)
        doc_collections_handler_function.grant_invoke(inference_principal)
        embeddings_provider_function.grant_invoke(inference_principal)
        ingestion_status_provider_function.grant_invoke(inference_principal)
        vector_store_provider_function.grant_invoke(inference_principal)

        bedrock_provider_function.grant_invoke(ingestion_principal)
        doc_collections_handler_function.grant_invoke(ingestion_principal)
        embeddings_provider_function.grant_invoke(ingestion_principal)
        vector_store_provider_function.grant_invoke(ingestion_principal)

        embeddings_provider_function.grant_invoke(vector_store_principal)
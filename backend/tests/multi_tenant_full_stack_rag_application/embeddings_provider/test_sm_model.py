import boto3
import json

client = boto3.client('sagemaker-runtime')


endpoint_name = 'tei-2025-09-04-15-14-22-917'
region_name='us-west-2'
text = {"inputs": "Gimme some digits"}
response = client.invoke_endpoint(
    EndpointName=endpoint_name,
    Body=json.dumps(text).encode('utf-8'),
    ContentType='application/json',
    Accept='*/*'
)
print(response)
body = json.loads(response['Body'].read())
print(body)
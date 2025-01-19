import boto3

cidp_client = boto3.client('cognito-idp')

next_token = ''
while next_token is not None:
    response = cidp_client.list_user_pools(MaxResults=50)
    pools = response['UserPools']
    for pool in pools:
        if pool['Name'].lower().startswith('mock_pool'):
            cidp_client.delete_user_pool(UserPoolId=pool['Id'])
    next_token = response['NextToken'] if 'NextToken' in response else None

cid_client = boto3.client('cognito-identity')
# print("Finished deleting user pools. Now deleting identity pools.")
next_token = ''
while next_token is not None:
    response = cid_client.list_identity_pools(MaxResults=50)
    # # print(f"Got response {response}")
    pools = response['IdentityPools']
    for pool in pools:
        if pool['IdentityPoolName'].lower().startswith('mock_pool'):
            cid_client.delete_identity_pool(IdentityPoolId=pool['IdentityPoolId'])
    next_token = response['NextToken'] if 'NextToken' in response else None
# print("Deletions complete")
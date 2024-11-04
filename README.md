# Multi-tenant, full-stack RAG application demo

## Goals
Welcome! The goal of this stack is to demonstrate:
* how to create a multi-tenant RAG application using AWS generative AI services.
* how to use OpenSearch Managed directly as a vector store provider.
* how to handle event-based ingestion of documents, without requiring manual or programmatic triggering of new document ingestion.
* how to implement sharing of document collections with other users.
* how to do multi-RAG query orchestration across multiple document collections
* how to do graph RAG, by providing example entity extraction pipelines and example prompt orchestration of user prompts across vector or graph databases, depending on the user prompt contents.

## Getting started
To get started, do the following. If you have CDK installed on your machine and working in your account alread, skip to [using a pre-existing CDK installation](#using-a-pre-existing-cdk-installation).

### Using the CDK deployment instance provided here.

1. If you don't have CDK working yet, the easiest way to get going will be to deploy the ec2 instance in [optional_deployment_assets/deployment-instance-template.yaml](optional_deployment_assets/deployment-instance-template.yaml) by going to your CloudFormation console, clicking create new stack, and uploading the deployment-instance-template.yaml file as a new template.

2. After the install completes, go to the EC2 console click on the running instance that just installed, and click on the Connect button at the top. Use the Session Manager connect option, and click Connect.

3. Once in the terminal, paste in the following command:

```
sudo su - cdkuser && cd multi-tenant-full-stack-rag-application-demo
```

4. Use your favorite terminal editor to edit the backend/cdk.context.json file. Specifically, you need to at least edit the `allowed_email_domains` configuration option, so that you'll be able to create users through the web sign-up form. You may also want to change the `app_name`, the `verification_email_subject`, and the `verification_email_body`. Finally, you can add your own IP address or range to the `os_dashboards_ec2_enable_traffic_from_ip` to allow you to connect to the OpenSearch Dashboards proxy EC2 instance.

5. Then add AWS credentials for a user or role you've created to the terminal session by setting these variables:

```
export AWS_ACCESS_KEY_ID="your aws access key ID"
export AWS_SECRET_ACCESS_KEY="your aws secret key"
# optionally, use the session token if you're using short term credentials instead of an IAM user (best practice)
export AWS_SESSION_TOKEN="your aws session token"
```

6. If you've never installed a CDK stack in this account and region, you'll need to bootstrap the region in that account. Run the following:

`cdk bootstrap aws://account_id/region` where `account_id` is your 12-digit AWS account ID and the region is the region code, like `us-west-2`.

7. Then run:

```
screen
./install_cdk.sh
```

Optionally add `-y` if you want to approve of the IAM changes it's going to prompt you for. If you don't use `-y`, be aware that there are multiple stacks being installed, and they'll all prompt you 

The `screen` command will make it so that if your installation session will be disconnected from your terminal session, so if you get disconnected, the install will continue.

If you do get disconnected, to reconnect to the screen from before, after reconnecting to the Session Manager terminal, type:

```
sudo su - cdkuser 
screen -r
```

And type <CTRL>+A and then D to disconnect from the screen and leave it runnning.

8. It may take take up to 60 minutes to deploy the whole stack, backend and frontend. At the end of the frontend deployment, it will print out the URL of the CloudFront distribution for the frontend UI. Click that to get started.

### Using your pre-installed CDK ### 

If you're familiar with using the CDK, and you already have your account bootstrapped, just do the following:

1. `git clone https://github.com/aws-samples/multi-tenant-full-stack-rag-application-demo.git`
2. `cd multi-tenant-full-stack-rag-application-demo`
3. paste your AWS credentials into the terminal
4. Bootstrap your account and region if you've never used CDK in this region (`cdk bootstrap aws://account_id/region_code`)
5. `./install_cdk.sh -y` (the -y is optional to approve all of the IAM changes, equivalent to running `cdk deploy --require-approval never`)

### Next steps after installation ###

1. When you first get to the login screen, use the create account tab and create a new user. You must use the same domain name you added to the cdk.context.json file in the allowed_email_domains list. If you skipped that part, you can create users in the Cognito console, or update the cdk.context.json file and rerun ./install_cdk.sh to reflect changes.

2. After setting up your Cognito user you should be able to log in.

3. Create a document collection and upload some documents. When creating the collection, use the description to describe specifically when to search this collection and when not to, as in the example below:

`Use this document collection for (fill in the use case here). Don't use it for other topics.`

* Click create document collection
![click create doc collection](./readme_assets/create_doc_collection1.png) 

* Enter details about the collection and click Save.
![add details and click submit](./readme_assets/create_doc_collection2.png)

* Upload files to the document collection
![upload_files](./readme_assets/upload_files.png)

4. Click on Start a Conversation in the left nav. Click the first Anthropic model for Haiku (`anthropic.claude-3-haiku-20240307-v1:0`), and start asking questions about your documents!

## Architecture

### Ingestion architecture
![Ingestion architecture](./readme_assets/ingestion_architecture.png)

### Inference architecture
![Inference architecture](./readme_assets/inference_architecture.png)

## Cost to run this stack

Update coming soon after I optimize the first version a bit.

## Feature status and roadmap
 | Feature | Status | Comments |
 |---------|--------|----------|
 | Event-based, highly parallel, serverless ingestion| complete | Uses S3 events -> SQS -> Lambda to process docs in real-time when they hit the S3 bucket. Currently, users can upload files into the UI directly. Future functionality will include bulk upload capabilities.|
 | Document collections CRUD | complete | Document collections are like Bedrock KBs, backed by OpenSearch managed. Web uploads currently supported. Bulk uploads require backend access for now, but will be supported in the future by a cross-platform client (like the WorkDocs client) that would allow easy syncing of whole folders. Also, will support accepting an S3 URI and a role with permissions to access it, to sync from a given bucket and path. | 
 | Prompt templates CRUD | complete | Prompt templates can be created/read/updated/deleted from the web UI, and associated with one or more models. For example, you can create a default template for all the Claude 3 models. | 
 | Text generation | complete | Chat history and current message are automatically evaluated for whether a RAG search is needed, given all of the user's current document collections. In the future, will add faceted search-style document collection inclusion/exclusion. | 
 | Model parameters in the UI | complete | Provide sliders for model parameters, like in the Bedrock chat playground. | 
 | Multi-RAG query orchestration with graph data and semantic search| complete |  Requires descriptive text in the document collections explaining with which subjects they are intended for use. | 
 | Ingestion status of files | complete | |
 | Entity extraction pipeline | complete | when enabled, uses Haiku and a given extraction template to store data in Neptune database. | 
 | Default prompts for each model family | complete |
  | Sharing document collections across users at the collection level | complete | Works like Quip where you can search for named users. Doesn't yet support asterisk for sharing with everyone who's logged in. |
 | Conversation history | in progress | The current conversation has memory but it doesn't yet offer saving of conversations. | 
  | Custom logos instead of "Multi-tenant full-stack rag demo" to enable customized field demos.| partially complete | no logos yet, but the app title is configurable through backend/cdk.context.json file. |
 | Saving conversation history | | |
 | Paging through long lists of uploaded files |||
 | Feedback | | |
 | Image generation | | |
 | Multi-modal queries | | |
 | Response streaming | | currently shows a "typing" gif, but not yet streaming.|
 | Allow user to specify that doc collections are optimized for long or short answers | | Currently optimized for longer answers which can also easily retrieve shorter answers to meet both needs in shortest term.|
 | Sharing document collections across users at the individual document level | unlikely to be soon | |
 | Looping to solve complex code generation for Q&A tasks. | | |
 | Add support for other doc types besides plain text| | right now it treats everything it doesn't recognize as plain text, so it can handle code files with any extension, for example, but doesn't do PDFs or Office docs yet. |
 | Add crawlers | | |




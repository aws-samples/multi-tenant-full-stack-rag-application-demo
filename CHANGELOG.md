* v0.1 - Initial public commit. Features include:
    *  Web UI that uses Cognito authentication and Cloudscape.design, with React, and some Recoil, but mostly uses React state still. 
        * Needs further conversion to recoil.
        * Likely still needs UI work for loading states and other
          improved feedback for users.
    * HTTP-API-based backend, that uses:
        * API Gateway with Cognito authentication, 
        * Lambda for compute
        * DynamoDB for storing user settings and system settings.
        * OpenSearch Managed for storing vectorized records
          with metadata for semantic search.
            * defaults to large chunks for more effective 
              Q&A results.
        * Neptune for storage of graph data extracted from 
          ingested documents via the entity extraction pipeline.
        * Bedrock for Titan Text Embeddings v2 and invocation of 
          all other Bedrock-hosted LLMs
    * Advanced features like:
        * Optimized, prescriptive chunking for maximum Q&A 
          effectiveness. 
            * Keeps paragraphs together
            * Keeps chunks large for greater context.
            * Works well for speed and accuracy with Haiku.
        * Automatic querying of relevant document collections at 
          chat time
        * Automatic usage of similarity search plus graph query
          for Q&A responses.
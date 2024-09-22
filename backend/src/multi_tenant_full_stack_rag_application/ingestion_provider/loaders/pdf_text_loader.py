#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import time

from datetime import datetime

from multi_tenant_full_stack_rag_application.utils import BotoClientProvider
from multi_tenant_full_stack_rag_application.ingestion_provider.loaders import Loader
from multi_tenant_full_stack_rag_application.ingestion_provider.splitters import Splitter

class PdfTextLoader(Loader):
    def __init__(self,*,
        s3: boto3.client,
        splitter: Splitter,
        textract: boto3.client,
        **kwargs
    ): 
        super().__init__(splitter)
        self.textract = textract
        self.s3 = s3

    def calculate_leading_newlines(self, last_height, last_top, top):
        if top - last_top > 3 * last_height:
            return "\n\n\n"
        elif top - last_top > 2 * last_height:
            return "\n\n"
        elif top - last_top > last_height:
            return "\n"
        else:
            return ''
    
    def load(self, bucket, s3_path):
        start_time = datetime.now().timestamp()
        response = self.textract.start_document_analysis(
            DocumentLocation={
                "S3Object": {
                    "Bucket": bucket,
                    "Name": s3_path
                }
            },
            FeatureTypes=['TABLES','FORMS','LAYOUT','SIGNATURES']
        )
        if response['ResponseMetadata']['HTTPStatusCode'] != 200: 
            raise Exception(f'Error processing s3://{bucket}/{s3_path}')
        
        job_id = response['JobId']
        results = self.textract.get_document_analysis(JobId=job_id)
        
        while results['JobStatus'] == 'IN_PROGRESS':
            # print('Job is in progress. Waiting for completion.')
            time.sleep(5)
            results = self.textract.get_document_analysis(JobId=job_id)
        
        # print(f"Status is now {results['JobStatus']}")
        if results['JobStatus'] != 'SUCCEEDED':
            raise Exception(f'Error processing s3://{bucket}/{s3_path}')
        
        next_token = None
        found_data = []
        while True:
            blocks = results['Blocks']
            for block in blocks:
                new_data = {
                    "block_type": block["BlockType"],
                    "page": block["Page"],
                    "id": block["Id"],
                    "geometry": block["Geometry"],
                }
                if "Text" in block:
                    new_data["text"] = block["Text"]
                if "Confidence" in block:
                    new_data["confidence"] = block["Confidence"]
                found_data.append(new_data)
            if "NextToken" in results:
                next_token = results["NextToken"]
                results = self.textract.get_document_analysis(JobId=job_id, NextToken=next_token)
            else:
                break
        # # print(f"found data {found_data}")

        output_text = ''
        last_height = 0
        last_top = 0
        for found_item in found_data:
            height = found_item["geometry"]["BoundingBox"]["Height"]
            top = found_item["geometry"]["BoundingBox"]["Top"]
            if found_item['block_type'] == 'PAGE':
                # print(found_item)
            if "text" in found_item:
                leading_newlines = self.calculate_leading_newlines(last_height, last_top, top)
                output_text += leading_newlines + found_item["text"] + " "
            last_height = height
            last_top = top
        ts = datetime.now().isoformat()
        with open(f'results/results-{ts}.txt', 'w') as f_out:
            f_out.write(output_text)

        return output_text

        




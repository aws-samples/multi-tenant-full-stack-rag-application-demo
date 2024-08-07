#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
from urllib.parse import unquote_plus

class VectorIngestionHandlerEvent:
    def from_lambda_event(self, event):
        print(f"VectorIngestionHandlerEvent received event {event}")
        self.ingestion_files = []
        for record in event["Records"]:
            print(f"Got top-level record {record}")
            self.rcpt_handle = record["receiptHandle"]
            self.evt_source_arn = record["eventSourceARN"]
            self.account_id = self.evt_source_arn.split(":")[4]
            if 'body' in record:
                body = json.loads(record["body"])
                print(f"Got event body {body}")
                event = ''
                if "Event" in body:
                    event = body["Event"]
                    
                if "Records" in body:
                    for rec in body["Records"]:
                        print(f"Got body rec {rec}")
                        key = rec["s3"]["object"]["key"]
                        parts = key.split("/")
                        self.user_id = unquote_plus(parts[1])
                        collection_id = parts[2]
                        filename = unquote_plus(parts[-1])
                        file = {
                            "account_id": self.account_id,
                            "bucket": rec["s3"]["bucket"]["name"],
                            "key": key,
                            "user_id": self.user_id,
                            "collection_id": collection_id,
                            "event": event,
                            "event_name":  rec["eventName"],
                            "filename": filename
                        }
                        if "eTag" in rec["s3"]["object"]:
                            file["etag"] = rec["s3"]["object"]["eTag"]
                        
                        self.ingestion_files.append(file)
                else:
                    print("No records in body")
            else:
                print("No body in event")
                print(event.keys())
        return self

    def __str__(self):
        args = {
            "ingestion_files": self.ingestion_files,
            "rcpt_handle": self.rcpt_handle,
            "evt_source_arn": self.evt_source_arn
        }
        return json.dumps(args)

#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

# This file is an improved version of Langchain's RecursiveCharacterTextSplitter.
# It improves upon the former by combining small chunks into larger chunks,
# to ensure that chunks are as close as possible to the max tokens per chunk without going over.
import os
from math import ceil

from multi_tenant_full_stack_rag_application import utils
from multi_tenant_full_stack_rag_application.ingestion_provider.splitters import Splitter

default_split_seqs = ['\n\n\n', '\n\n', '\n', '. ', ' ']

class OptimizedParagraphSplitter(Splitter):
    def __init__(self, *,
        max_tokens_per_chunk: int,
        lambda_client=None,
        ssm_client=None,
        split_seqs=default_split_seqs,
    ):
        super().__init__(
            max_tokens_per_chunk=max_tokens_per_chunk, 
            split_seqs=split_seqs
        )
        
        self.utils = utils
        
        if not lambda_client:
            self.lambda_ = self.utils.BotoClientProvider.get_client('lambda')
        else:
            self.lambda_ = lambda_client

        if not ssm_client:  
            self.ssm = self.utils.BotoClientProvider.get_client('ssm')
        else:
            self.ssm = ssm_client

        self.split_seqs = split_seqs
        
        stack_name = os.getenv('STACK_NAME')
    
        # self.emb_provider_fn_name = self.utils.get_ssm_params('embeddings_provider_function_name')
    
        self.max_tokens_per_chunk = max_tokens_per_chunk

    def get_model_max_tokens(self, model_id):
        if not self.max_tokens_per_chunk:
            # response = invoke_lambda(
            #     self.emb_provider_fn_name, 
            #     {
            #         'operation': 'get_model_max_tokens',
            #         'origin': self.utils.get_ssm_params('ingestion_provider_function_name'),
            #         'args': {
            #             'model_id': model_id
            #         }
            #     }, 
            #     lambda_client=self.lambda_
            # )
            print(f"response from get_model_max_tokens: {response}")
            self.max_tokens_per_chunk = json.loads(response['body'])['response']
        print(f"Got max_tokens_per_chunk {self.max_tokens_per_chunk}")
        return self.max_tokens_per_chunk

    # def get_token_count(self, text):
    #     return invoke_lambda(
    #         self.emb_provider_fn_name, 
    #         {'operation': 'get_token_count', 'text': content}, 
    #         lambda_client=self.lambda_
    #     )

    def split(self, content, source, *, extra_header_text='', extra_metadata={}, return_dicts=False, split_seq_num=0):
        print(f"OptimizedParagraphSplitter got content {content}")
        results = []
        content = content.replace('\xa0', '')
        content = content.replace('\t','')
        split_seq = self.split_seqs[split_seq_num]
        header_len = self.utils.get_token_count(extra_header_text)
        text_len = self.utils.get_token_count(content)
        print(f"Got header_len {header_len} and text_len {text_len}")
        # header_len = self.emb_provider_fn_name.get_token_count(extra_header_text)
        # text_len = self.emb_provider_fn_name.get_token_count(content)
        token_ct = header_len + text_len
        if token_ct <= self.max_tokens_per_chunk:
            print(f"Token count is less than max tokens. Keeping it all one chunk.")
            results = [f"{extra_header_text}\n{content}"]
        else:
            parts = content.split(self.split_seqs[split_seq_num])
            if not isinstance(parts, list):
                parts = [parts]
            print(f"Got {len(parts)} parts after splitting with split_seq {self.split_seqs[split_seq_num]}")
            # aggregate parts back together so they approach the desired max tokens
            # per chunk.
            running_part = ''
            running_part_toks = 0
            for part in parts:
                if part.strip() == '':
                    continue
                part += split_seq
                num_toks = self.utils.get_token_count(part)
                # num_toks = self.emb_provider_fn_name.get_token_count(part)
                if running_part_toks + num_toks < self.max_tokens_per_chunk:
                    running_part += ' ' + part
                    running_part_toks += num_toks
                else: 
                    # The running part is full. Append to the results array.
                    if running_part != '':
                        print(f"Appending running part to results ({len(running_part.split())} words)")
                        results.append(f"{extra_header_text} {running_part}")
                        running_part = ''
                        running_part_toks = 0
                    # Now check how to handle the current part. If this chunk is too big by itself 
                    # to fit in the max_tokens_per_chunk, split it. Otherwise, just us it as
                    # the beginning of a new running part.
                    if num_toks > self.max_tokens_per_chunk:
                        print(f"Recursing because the number of tokens is still too big {num_toks}.")
                        results += self.split(
                            part, 
                            source,
                            extra_header_text=extra_header_text, 
                            extra_metadata=extra_metadata,
                            split_seq_num=split_seq_num + 1
                        )
                    else:
                        running_part = part
                        running_part_toks = num_toks

            results.append(f"{extra_header_text} {running_part}")   
        print(f"optimized paragraph splitter returning {results}")  
        return results
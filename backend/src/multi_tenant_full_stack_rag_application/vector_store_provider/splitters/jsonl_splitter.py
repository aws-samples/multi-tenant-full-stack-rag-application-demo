#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider import EmbeddingsProvider
from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider_factory import EmbeddingsProviderFactory
from multi_tenant_full_stack_rag_application.vector_store_provider.splitters import Splitter
import json


# Not used. Reads in jsonlines until the current
# chunk is maxed, then goes to the next chunk 
# and adds a new header
default_split_seqs = []


class JsonlSplitter(Splitter):
    def __init__(self, 
        emb_provider: EmbeddingsProvider,
        max_tokens_per_chunk: int = 0,
        split_seqs = default_split_seqs
    ):
        self.emb_provider = emb_provider
        if max_tokens_per_chunk == 0:
            self.max_tokens_per_chunk = self.emb_provider.get_model_max_tokens()
        else:
            self.max_tokens_per_chunk = max_tokens_per_chunk
        self.split_seqs = split_seqs

    def split(self, records, path, source, *, one_doc_per_line=False, extra_metadata={}, extra_header_text='', split_seq_num=0, return_dicts=True):
        filename = path.split('/')[-1]
        header = ''
        chunks = []
        curr_chunk = ''
        running_token_total = 0
        ctr = 0
        for row in records:
            if not one_doc_per_line:
                if header == '':
                    header = extra_header_text
                    curr_chunk += header
                    running_token_total += self.estimate_tokens(header)
                curr_token_ct = self.estimate_tokens(json.dumps(row) + "\n")
                if running_token_total + curr_token_ct > self.emb_provider.get_model_max_tokens():
                    chunks.append(curr_chunk)
                    print(f"Logged chunk: {curr_chunk}")
                    curr_chunk = header
                    running_token_total = 0
                    running_token_total += self.estimate_tokens(header)
                    curr_chunk += json.dumps(row) + "\n"
                    running_token_total += curr_token_ct
                else:
                    curr_chunk += json.dumps(row) + "\n"
                    print(f"Logged chunk: {curr_chunk}")
                    running_token_total += curr_token_ct
                if running_token_total > self.emb_provider.get_model_max_tokens():
                    raise Exception(f'Row is going to need splitting because it\'s over {self.emb_provider.get_model_max_tokens()} tokens long:\n{row}')
                chunks.append(curr_chunk)
                print(f"Logged csv_chunk: {curr_chunk}")
            else:
                if extra_header_text != '':
                    extra_header_text += "\n"
                chunks.append(f"{extra_header_text}{json.dumps(row)}\n")
        return chunks
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

# This file is an improved version of Langchain's RecursiveCharacterTextSplitter.
# It improves upon the former by combining small chunks into larger chunks,
# to ensure that chunks are as close as possible to the max tokens per chunk without going over.
from math import ceil

from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider import EmbeddingsProvider
from multi_tenant_full_stack_rag_application.vector_store_provider.splitters import Splitter

default_split_seqs = ['\n\n\n', '\n\n', '\n', '. ', ' ']

class OptimizedParagraphSplitter(Splitter):
    def __init__(self, 
        emb_provider: EmbeddingsProvider,
        max_tokens_per_chunk: int = 0,
        split_seqs = default_split_seqs
    ):
        super().__init__(emb_provider, max_tokens_per_chunk, split_seqs)
        self.emb_provider = emb_provider
        if max_tokens_per_chunk == 0:
            self.max_tokens_per_chunk = emb_provider.get_model_max_tokens()
        else:
            self.max_tokens_per_chunk = max_tokens_per_chunk
        self.split_seqs = split_seqs

    def split(self, content, source, *, extra_header_text='', extra_metadata={}, return_dicts=False, split_seq_num=0):
        results = []
        content = content.replace('\xa0', '')
        content = content.replace('\t','')
        split_seq = self.split_seqs[split_seq_num]
        header_len = self.emb_provider.get_token_count(extra_header_text)
        text_len = self.emb_provider.get_token_count(content)
        token_ct = header_len + text_len
        if token_ct <= self.max_tokens_per_chunk:
            results = [f"{extra_header_text}\n{content}"]
        else:
            parts = content.split(self.split_seqs[split_seq_num])
            if not isinstance(parts, list):
                parts = [parts]
            # aggregate parts back together so they approach the desired max tokens
            # per chunk.
            running_part = ''
            running_part_toks = 0
            for part in parts:
                if part.strip() == '':
                    continue
                part += split_seq
            
                num_toks = self.emb_provider.get_token_count(part)
                if running_part_toks + num_toks < self.max_tokens_per_chunk:
                    running_part += ' ' + part
                    running_part_toks += num_toks
                    
                else: 
                    # The running part is full. Append to the results array.
                    if running_part != '':
                        results.append(f"{extra_header_text} {running_part}")
                        running_part = ''
                        running_part_toks = 0
                    # Now check how to handle the current part. If this chunk is too big by itself 
                    # to fit in the max_tokens_per_chunk, split it. Otherwise, just us it as
                    # the beginning of a new running part.
                    if num_toks > self.max_tokens_per_chunk:
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
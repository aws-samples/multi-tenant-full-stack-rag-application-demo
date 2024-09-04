#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from abc import ABC, abstractmethod
from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider import EmbeddingsProvider


class Splitter(ABC):
    def __init__(self, 
        emb_provider: EmbeddingsProvider,
        max_tokens_per_chunk: int = 0,
        split_seqs = [],
        **kwargs
    ):
        self.emb_provider = emb_provider
        self.split_seqs = split_seqs
    
    @staticmethod
    def estimate_tokens(text):
        return len(text.split()) * 1.3

    @abstractmethod
    def split(self, content, path, source, *, extra_header_text='', extra_metadata={}, split_seq_num=0):
        pass
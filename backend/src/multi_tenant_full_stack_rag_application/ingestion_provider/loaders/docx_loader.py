#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import pypandoc as pypd
import shutil
import zipfile
from datetime import datetime

from multi_tenant_full_stack_rag_application.ingestion_provider.splitters.jsonl_splitter import JsonlSplitter
from multi_tenant_full_stack_rag_application.ingestion_provider.splitters.optimized_paragraph_splitter import OptimizedParagraphSplitter
from multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_document import VectorStoreDocument

from multi_tenant_full_stack_rag_application import utils
from .loader import Loader
from .text_loader import TextLoader
from .xlsx_loader import XlsxLoader


class DocxLoader(Loader):
    def __init__(self, *, splitter):
        self.splitter = splitter
        self.utils = utils
        self.my_origin = self.utils.get_ssm_params("origin_ingestion_provider")


    def check_for_embedded_docs(self, path):
        zipfile_path = path.replace('.docx', '.zip')
        shutil.copy(path, zipfile_path)
        embedded_doc_paths = []
        with zipfile.ZipFile(zipfile_path, 'r') as zip_ref:
            for name in zip_ref.namelist():
                if name.startswith('word/embeddings'):
                    zip_ref.extract(name)
                    new_name = path.replace('.docx', '_') + name.split('/')[-1]
                    shutil.move(name, new_name)
                    embedded_doc_paths.append(new_name)
        return embedded_doc_paths

    def load(self, path):
        if not path.endswith('.docx'):
            msg = f'File {path} is not a docx.'
            if path.endswith('.doc'):
                msg += " Older .doc files are not supported."
            raise Exception(msg)
        text = pypd.convert_file(path, 'markdown', extra_args=['--quiet'])
        # print(f"pypandoc extracted text from word doc: {text}")
        embedded_doc_paths = self.check_for_embedded_docs(path)
        print(f"Got embedded doc paths {embedded_doc_paths}")
        if len(embedded_doc_paths) == 0:
            text += "\n\n<attachments>\n"
            for emb_path in embedded_doc_paths:
                text += "\n<attachment>\n"
                text += f"<filename>{emb_path}</filename>\n<content>"
                
                if emb_path.endswith('.xlsx'):
                    jsonl_splitter = JsonlSplitter(self.emb_provider)
                    docs = XlsxLoader(self.emb_provider, jsonl_splitter).load_and_split_text(emb_path, emb_path, one_doc_per_line=False)
                elif doc.endswith('.docx'):
                    docs = DocxLoader().load(emb_path)
                else:
                    # default to the text loader
                    docs = TextLoader(
                        emb_provider=self.emb_provider, 
                        splitter=self.splitter
                    ).load_and_split_text(emb_path, emb_path)

                docs_txt = ''
                for doc in docs:
                    docs_txt += doc.content + "\n"
                text +=  docs_txt
                text += "</content>\n</attachment>\n"
            text+= "\n</attachments>"
        print(f"DocxLoader returning text {text}")
        return text
        
    def load_and_split(self, path, user_id, source=None, *, extra_metadata={}, extra_header_text='', one_doc_per_line=False, return_dicts=False):
        if not source:
            source = path
        collection_id = source.split('/')[-2]
        filename = path.split('/')[-1]
        self.utils.set_ingestion_status(
            user_id, 
            f"{collection_id}/{filename}",
            '',
            0, 
            'IN_PROGRESS',
            self.utils.get_ssm_params('origin_ingestion_provider')
        )
        try: 
            content = self.load(path)
            print(f"Got content to split: {content}")
            docs = []
            if not 'source' in extra_metadata:
                extra_metadata['source'] = source
            if not 'title' in extra_metadata:
                extra_metadata['title'] = filename
            if 'FILENAME' not in extra_header_text.upper():
                extra_header_text += f"\nFILENAME: {filename}\n{extra_header_text}\n"
                extra_header_text = extra_header_text.replace("\n\n", "\n").lstrip("\n")
            extra_metadata['upsert_date'] = datetime.now().isoformat()
            text_chunks = self.splitter.split(
                content,
                source,
                extra_header_text=extra_header_text,
                extra_metadata=extra_metadata
            )
            print(f"Got text_chunks {text_chunks}")
            ctr = 0
            for chunk in text_chunks:
                id = f"{source}:{ctr}"
                vector = self.utils.embed_text(chunk, self.my_origin)
                print(f"Creating doc with id {id}")
                if not return_dicts:
                    docs.append(VectorStoreDocument(
                        id,
                        chunk,
                        extra_metadata,
                        vector
                    ))
                else:
                    docs.append({
                        'id': id,
                        'content': chunk,
                        'metadata': extra_metadata,
                        'vector': vector
                    })
                ctr += 1
            return docs
        except Exception as e:
            print(f"Error loading {path}: {e}")
            self.utils.set_ingestion_status(
                user_id, 
                f"{collection_id}/{filename}",
                '',
                0, 
                f'ERROR: {e.__dict__}',
                self.utils.get_ssm_params('origin_ingestion_provider')
            )
            raise e
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import pypandoc as pypd
import shutil
import zipfile

from multi_tenant_full_stack_rag_application.ingestion_provider.splitters.jsonl_splitter import JsonlSplitter

from .loader import Loader
from .text_loader import TextLoader
from .xlsx_loader import XlsxLoader

class DocxLoader(Loader):
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
        text = pypd.convert_file(path, 'plain', extra_args=['--quiet'])
        embedded_doc_paths = self.check_for_embedded_docs(path)
        if len(embedded_doc_paths) == 0:
            text += "\n\n<attachments>\n"
        for emb_path in embedded_doc_paths:
            text += "\n<attachment>\n"
            text += f"<filename>{emb_path}</filename>\n<content>"
            
            if emb_path.endswith('.xlsx'):
                jsonl_splitter = JsonlSplitter(self.emb_provider)
                docs = XlsxLoader(self.emb_provider, jsonl_splitter).load_and_split_text(emb_path, emb_path, one_doc_per_line=False)
            elif doc.endswith('.docx'):
                docs = DocxLoader(self.emb_provider, self.splitter).load_and_split_text(emb_path, emb_path)
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
        return text
        
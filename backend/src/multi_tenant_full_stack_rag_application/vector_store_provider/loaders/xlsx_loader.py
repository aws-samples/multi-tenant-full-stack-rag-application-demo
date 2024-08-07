#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import pandas as pd
from .loader import Loader


class XlsxLoader(Loader):
    def load(self, path):
        if not path.endswith('.xlsx'):
            msg = f'File {path} is not a xlsx.'
            if path.endswith('.xls'):
                msg += " Older .xls files are not supported."
            raise Exception(msg)
        df = pd.read_excel(path)
        df.ffill(inplace=True)
        records = df.to_dict('records')
        return records

    def load_and_split(self, path, source, *, extra_metadata={}, extra_header_text='', return_dicts=False):
        pass
        #     records = self.load(path)
        #     print(f"splitting path {path}")
        #     filename = source.split('/')[-1]

        #     if not 'source' in extra_metadata:
        #         extra_metadata['source'] = source
        #     if not 'title' in extra_metadata:
        #         extra_metadata['title'] = filename
        #     return self.split_records(records, path, return_dicts)

    

            
        
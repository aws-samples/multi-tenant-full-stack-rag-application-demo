#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from multi_tenant_full_stack_rag_application.ingestion_provider.splitters import Splitter


# Not used. Reads in lines until the current
# chunk is maxed, then goes to the next chunk 
# and adds a new header
default_split_seqs = []


class CsvSplitter(Splitter):
    def __init__(self, 
        max_tokens_per_chunk: int = 0,
        split_seqs = default_split_seqs
    ):
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.split_seqs = split_seqs

    def convert_dict_to_csv_row(self, row_dict, *, get_header=False):
        response = ''
        for key in row_dict:
            if get_header:
                if ',' in key:
                    if '"' in key:
                        key = key.replace('"', '\"')
                    key = f"\"{key}\""
                response += f"{key},"
                # print()
            else:
                value = str(row_dict[key])
                if ',' in value:
                    if '"' in value:
                        value = value.replace('"', '\"')
                    value = f"\"{value}\""
                response += f"{value},"     
            response = response.strip(',') + "\n"
        return response

    def split(self, records, path, source, *, extra_metadata={}, extra_header_text='', split_seq_num=0, return_dicts=True):
        filename = path.split('/')[-1]
        header = ''
        csv_chunks = []
        curr_csv_chunk = ''
        running_token_total = 0
        ctr = 0
        for record in records:
            if header == '':
                header = self.convert_dict_to_csv_row(record, get_header=True)
                curr_csv_chunk += header
                running_token_total += self.estimate_tokens(header)
            row = self.convert_dict_to_csv_row(record)
            curr_token_ct = self.estimate_tokens(row)
            if running_token_total + curr_token_ct > self.max_tokens_per_chunk:
                csv_chunks.append(curr_csv_chunk)
                # print(f"Logged csv_chunk: {curr_csv_chunk}")
                curr_csv_chunk = header
                running_token_total = 0
                running_token_total += self.estimate_tokens(header)
                curr_csv_chunk += row
                running_token_total += curr_token_ct
            else:
                curr_csv_chunk += row
                # print(f"Logged csv_chunk: {curr_csv_chunk}")
                running_token_total += curr_token_ct
            if running_token_total > self.max_tokens_per_chunk:
                raise Exception(f'Row is going to need splitting because it\'s over {self.max_tokens_per_chunk} tokens long:\n{row}')
        csv_chunks.append(curr_csv_chunk)
        # print(f"Logged csv_chunk: {curr_csv_chunk}")
        return csv_chunks
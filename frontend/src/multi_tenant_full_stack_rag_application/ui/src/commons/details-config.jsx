// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from 'react';
import { Link } from '@cloudscape-design/components';


export const DOCUMENT_COLLECTIONS_COLUMN_DEFINITIONS = [
  {
    id: 'collection_name',
    header: 'Collection Name',
    cell: item => item.collection_name,
    key: item => item.key,
    isRowHeader: true,
  },
  {
    id: 'description',
    header: 'Description',
    cell: item => item.description,
    key: item => item.key,
  },
  // {
  //   id: 'vector_db_type',
  //   header: 'Vector Engine',
  //   cell: item => item.vector_db_type,
    
  // },
  {
    id: 'updated_date',
    header: 'Last Updated',
    cell: item => item.updated_date,
  },
  // {
  //   id: 'status',
  //   header: 'Status',
  //   cell: item => item.status,
  //   isRowHeader: true
  // }
];

export const SHARING_LIST_COLUMN_DEFINITIONS = [
  {
    id: 'key',
    header: 'User Email',
    cell: item => item.key,
    key: item => item.key,
    isRowHeader: true,
  },
  {
    id: 'access',
    header: 'Access Level',
    cell: item => 'read all docs in collection'
  }
];

export const UPLOADED_DOCUMENTS_COLUMN_DEFINITIONS = [
  {
    id: 'file_name',
    header: 'File Name',
    cell: item => item.file_name,
    key: item => item.key,
    isRowHeader: true,
  },
  {
    id: 'last_modified',
    header: 'Last Modified',
    cell: item => item.last_modified
  },
  {
    id: 'ingestion_status',
    header: 'Ingestion Status',
    cell: item => item.status,
    isRowHeader: true
  }
];

export const PROMPT_TEMPLATES_COLUMN_DEFINITIONS = [
  {
    id: 'template_name',
    header: 'Template Name',
    cell: item => item.template_name,
    key: item => item.key,
    isRowHeader: true,
  },
  {
    id: 'template_text',
    header: 'Template Text',
    cell: item => item.template_text, //.replaceAll("\n", "\\n"),
    maxWidth: 300
  },
  {
    id: 'llm',
    header: 'LLMS',
    cell: item => item.model_ids,
    maxWidth: 200
    
  },
  {
    id: 'updated_date',
    header: 'Last Updated',
    cell: item => item.updated_date,
  }
];

export const INVALIDATIONS_COLUMN_DEFINITIONS = [
  {
    id: 'id',
    header: 'Invalidation ID',
    isRowHeader: true,
  },
  {
    id: 'status',
    header: 'Status',
  },
  {
    id: 'date',
    header: 'Date',
  },
];

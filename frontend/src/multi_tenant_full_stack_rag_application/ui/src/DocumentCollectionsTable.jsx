//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { useState, useEffect } from 'react';
import { DOCUMENT_COLLECTIONS_COLUMN_DEFINITIONS } from './commons/details-config';
import { logsTableAriaLabels } from './commons/commons';
import Api from './commons/api'
import { Box, Button, ButtonDropdown, Container, FileUpload, FormField, Header, SpaceBetween, Spinner, Table } from '@cloudscape-design/components';
import { atom, useRecoilState, useResetRecoilState, useRecoilValue } from 'recoil';
import { currentCollectionState } from './DocumentCollectionForm'

import "./documentCollectionsTable.css"

export const docCollectionsState = atom({
  key: 'DocumentCollectionsTable.docCollectionsState',
  default: []
})

export const addDocShareUserModalState = atom({
  key: 'DocumentCollectionForm.addDocShareUserModalState',
  default: null
})


export const addDocShareUserModalVisibleState = atom({
  key: 'DocumentCollectionForm.addDocShareUserModalVisibleState',
  default: false
})


export const isLoadingState = atom({
  key: 'DocumentCollectionForm.isLoadingState',
  default: true
})


export const isDeletingState = atom({
  key: 'DocumentCollectionForm.isDeletingState',
  default: false
})


export const shareListState = atom({
  key: 'DocumentCollectionForm.shareListState',
  default: null
})


export const confirmationModalState = atom({
  key: 'DocumentCollectionForm.confirmationModalState',
  default: null
})


export const currentPageIndexState = atom({
  key:  'DocumentCollectionForm.currentPageIndexState',
  default: 0
})

async function getTableProvider() {
  const api = new Api()
  return await api.getDocCollections();
}


function DocumentCollectionsTable() {
  useResetRecoilState(currentCollectionState)();
  const [docCollections, setDocCollections] = useRecoilState(docCollectionsState);
  // const [files, setFiles] = useState([]);
  const [selectedItem, setSelectedItem] = useState({});
  const [currentCollection, setCurrentCollection] = useRecoilState(currentCollectionState);
  // const [currentCollectionContents, setCurrentCollectionContents] = useState();
  // const atLeastOneSelected = selectedItem ? true :  false;
  const [tableData, setTableData] = useState([])
  const [tableLoadingState, setTableLoadingState] = useState(true)

  useEffect(() => {
    (async () => {
      setTableLoadingState(true)
      let collections = await getTableProvider()
      let tmpTableData = []
      let tmpDocCollections = []
      console.log("Got docCollections:")
      console.dir(collections)
      
      collections.forEach(collection => {
          let disabled = false
          let cn = (' ' + collection.collection_name).slice(1)
          // console.log("Got collection:")
          // console.dir(collection)
          // console.log(`vector_db_type = ${collection.vector_db_type}`)
          if (collection.vector_db_type != 'shared') {
            cn = <a title={cn} href={`/#/document-collections/${collection.collection_id}/edit`}>{cn}</a>
          }
          else {
            // console.log("shared collection...disabling row.")
            disabled = true
          }
          // console.log(`should this row be disabled? ${disabled}`)
          let newTableRow = {
            collection_id: collection.collection_id,
            collection_name: cn,
            description: collection.description,
            updated_date: collection.updated_date,
            vector_db_type: collection.vector_db_type,
            disabled: disabled
          }
          // console.log("got newCollection:")
          // console.dir(newCollection)
          tmpTableData.push(newTableRow)
          let newCollection = {...newTableRow}
          // remove the link from the collection name and save it
          // for use in drop-downs elsewhere, like ChatPlayground.jsx
          newCollection.collection_name = (' ' + collection.collection_name).slice(1)
          tmpDocCollections.push(newCollection)
      })
      setTableData(tmpTableData)
      setDocCollections(tmpDocCollections)
    })()
  }, [])

  useEffect(() =>{
    if (tableData) {
      // console.log("docCollections changed")
      // console.dir(docCollections)
      setTableLoadingState(false)
    }
    // setTableLoadingState(false)
    // // console.log("set tableLoadingState to false")
  }, [tableData])

  function showDetails(selected) {
    // // console.log("ShowDetails got selected");
    // // console.dir(selected)
    setSelectedItem(selected)
    setCurrentCollection(selected)
  }

  if (tableLoadingState) {
    return (
      <>
        <div style={{textAlign: "center"}}>
          Loading<br/>
          <Spinner size="large"/>
        </div>
      </>
    )
  }
  else {
    return (
      <>
        <Table
          className="documentCollectionsTable"
          columnDefinitions={DOCUMENT_COLLECTIONS_COLUMN_DEFINITIONS}
          items={tableData}
          wrapLines='true'
          loadingText="Loading document collections"
          loading={tableLoadingState}
          ariaLabels={logsTableAriaLabels}
          selectionType="single"
          selectedItems={[selectedItem]}
          onSelectionChange={({ detail }) =>
            showDetails(detail.selectedItems[0])
          }
          isItemDisabled={item =>{
            // console.log("Got item")
            // console.dir(item)
            if (item.vector_db_type == 'shared') {
              return true
            }
          }}
          header={
            <Header
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <ButtonDropdown
                    items={[
                      {
                        id: "edit",
                        disabled: !currentCollection,
                        text: "Edit or delete collection",
                        href: `/#/document-collections/${currentCollection ? currentCollection.collection_id : 'none'}/edit`,
                        // external: true,
                        // externalIconAriaLabel: "(opens in new tab)"
                      }
                    ]}
                  >
                    Actions
                  </ButtonDropdown>
                  <Button href="/#/document-collections/create" variant="primary">Create new document collection</Button>
                </SpaceBetween>
              }
            >
              Document Collections
            </Header>
          }
          footer={
            <Box textAlign="center">
              {/*<Link href="#">View all documentollections</Link>*/}
            </Box>
          }
        />
      </>
    );
  }
}


export default DocumentCollectionsTable;
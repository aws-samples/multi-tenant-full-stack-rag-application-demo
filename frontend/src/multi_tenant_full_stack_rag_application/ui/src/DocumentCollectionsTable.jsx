//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { useState, useEffect } from 'react';
import { DOCUMENT_COLLECTIONS_COLUMN_DEFINITIONS } from './commons/details-config';
import { logsTableAriaLabels } from './commons/commons';
import Api from './commons/api'
import { Box, Button, ButtonDropdown, Container, FileUpload, FormField, Header, SpaceBetween, Spinner, Table } from '@cloudscape-design/components';
import { atom, selector, useRecoilState, useRecoilValue } from 'recoil';
import "./documentCollectionsTable.css"


async function getTableProvider() {
  const api = new Api()
  return await api.getDocCollections();
}

export const collectionIsLoadingState = atom({
  key: 'DocumentCollectionsTable.iIsLoadingState',
  default: true
})

function DocumentCollectionsTable() {
  const [docCollections, setDocCollections] = useState([]);
  const [files, setFiles] = useState([]);
  const [selectedItem, setSelectedItem] = useState({});
  const [currentCollection, setCurrentCollection] = useState();
  // const [currentCollectionContents, setCurrentCollectionContents] = useState();
  // const atLeastOneSelected = selectedItem ? true :  false;
  const [tableLoadingState, setTableLoadingState] = useState(true)

  useEffect(() => {
    (async () => {
      setTableLoadingState(true)
      let collections = await getTableProvider()
      let tableData = []
      // console.log("Got docCollections:")
      // console.dir(collections)
      collections.forEach(collection => {
        let disabled = false
        // console.log("Got collection:")
        // console.dir(collection)
        let cn = collection.collection_name
        // console.log(`vector_db_type = ${collection.vector_db_type}`)
        if (collection.vector_db_type != 'shared') {
          cn = <a title={cn} href={`/#/document-collections/${collection.collection_id}/edit`}>{cn}</a>
          // console.log("vector db != 'shared'. cn is now:")
          // console.dir(cn)
        }
        else {
          // console.log("shared collection...disabling row.")
          disabled = true
        }
        // console.log(`should this row be disabled? ${disabled}`)
        let newCollection = {
          collection_id: collection.collection_id,
          collection_name: cn,
          description: collection.description,
          updated_date: collection.updated_date,
          vector_db_type: collection.vector_db_type,
          disabled: disabled
        }
        // console.log("got newCollection:")
        // console.dir(newCollection)
        tableData.push(newCollection)
      })
      setDocCollections(tableData)
    })()
  }, [])

  useEffect(() =>{
    if (docCollections) {
      // console.log("docCollections changed")
      // console.dir(docCollections)
      setTableLoadingState(false)
    }
    // setTableLoadingState(false)
    // // console.log("set tableLoadingState to false")
  }, [docCollections])

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
          items={docCollections}
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
              //counter={!docCollectionsLoading && getHeaderCounterText(docCollections, selectedItems)}
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
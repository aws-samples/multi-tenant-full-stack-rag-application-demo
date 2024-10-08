//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { useEffect } from 'react';
import Api from './commons/api';
import { Button, Container, Form, FormField, Header, Input, SpaceBetween, Spinner, Tabs } from '@cloudscape-design/components';
import { json, useParams } from 'react-router-dom';
import DeleteConfirmationModal from './DeleteConfirmationModal'
import DocumentCollection from './DocumentCollection'
import DocumentCollectionEnrichmentPipelines from './DocumentCollectionEnrichmentPipelines'
import DocumentCollectionSharingList from './DocumentCollectionSharingList'
import DocumentCollectionUploadedDocumentsTable from './DocumentCollectionUploadedDocumentsTable'
import { atom, useRecoilState, useRecoilValue, RecoilEnv } from 'recoil'

RecoilEnv.RECOIL_DUPLICATE_ATOM_KEY_CHECKING_ENABLED = false

const api = new Api();


async function getTableProvider(urlCollectionId, limit=20, lastEvalKey='') {
  //// console.log("newApi:")
  //// console.dir(provider)
  const data = await api.listUploadedFiles(urlCollectionId, limit, lastEvalKey);
  console.log("getTableProvider received data:")
  console.dir(data)
  return data;
}

const defaultEngine = "opensearch_managed"
const deleteModalMessageTemplate = `Are you sure you want to delete document collection "{currentCollection.name}?"`
const filePageSize = 20


function createVectorOption(val) {
  let parts = val.split('_')
  let label = parts[0][0].toUpperCase() + parts[0].slice(1) + ' ' +
    parts[1][0].toUpperCase() + parts[1].slice(1)
  return {
    "key": val,
    "label": label,
    "value": val
  }
}

export const urlCollectionIdState = atom({
  key: 'DocumentCollectionForm.urlCollectionIdState',
  default: null
})

export const currentCollectionState = atom({
  key: 'DocumentCollectionForm.currentCollectionState',
  default: {}
})

export const addUserModalState = atom({
  key: 'DocumentCollectionForm.addUserModalState',
  default: null
})

export const addUserModalVisibleState = atom({
  key: 'DocumentCollectionForm.addUserModalVisibleState',
  default: false
})

export const collectionIsLoadingState = atom({
  key: 'DocumentCollectionForm.collectionIsLoadingState',
  default: true
})

export const collectionIsDeletingState = atom({
  key: 'DocumentCollectionForm.collectionIsDeletingState',
  default: false
})

export const collectionShareListState = atom({
  key: 'DocumentCollectionForm.collectionShareListState',
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

export const deleteConfirmationMessageState = atom({
  key: 'DocumentCollectionForm.deleteConfirmationMessageState',
  default: `Are you sure you want to delete this document collection?
    {currentCollection.name}
  `
})

export const deleteModalVisibleState = atom({
  key: 'DocumentCollectionForm.deleteModalVisibleState',
  default: false
})

export const filesValState = atom({
  key: 'DocumentCollectionForm.filesValState',
  default: []
})

export const filesValIsLoadingState = atom({
  key: 'DocumentCollectionForm.filesValIsLoadingState',
  default: true
})

export const lastEvalKeyState = atom({
  key: 'DocumentCollectionForm.lastEvalKeyState',
  default: '' 
})

export const paramsState = atom({
  key: 'DocumentCollectionForm.paramsState',
  default: null
})

export const selectedVectorEngineState = atom({
  key: 'DocumentCollectionForm.selectedVectorEngineState',
  default: createVectorOption(defaultEngine)
})

export const submitDisabledState = atom({
  key: 'DocumentCollectionForm.submitDisabledState',
  default: true
})

export const uploadedFilesState = atom({
  key: 'DocumentCollectionForm.uploadedFilesState',
  default: []
})


function DocumentCollectionForm() {
  
  let tmpParams = useParams()
  const [urlCollectionId, setUrlCollectionId] = useRecoilState(urlCollectionIdState)
  const [currentCollection, setCurrentCollection ] = useRecoilState(currentCollectionState)
  const [addUserModal, setAddUserModal] = useRecoilState(addUserModalState)
  const [addUserModalVisible, setAddUserModalVisible] = useRecoilState(addUserModalVisibleState)
  const [collectionShareList, setCollectionShareList] = useRecoilState(collectionShareListState)
  const [confirmationModal, setConfirmationModal] = useRecoilState(confirmationModalState)
  const [currentPageIndex, setCurrentPageIndex] = useRecoilState(currentPageIndexState)
  const [deleteConfirmationMessage, setDeleteConfirmationMessage] = useRecoilState(deleteConfirmationMessageState)
  const [deleteModalVisible, setDeleteModalVisible] = useRecoilState(deleteModalVisibleState)
  const [filesVal, setFilesVal] = useRecoilState(filesValState)
  const [isLoading, setIsLoading] = useRecoilState(collectionIsLoadingState)
  const [isDeleting, setIsDeleting] = useRecoilState(collectionIsDeletingState)
  const [lastEvalKey, setLastEvalKey] = useRecoilState(lastEvalKeyState)
  const [params, setParams] = useRecoilState(paramsState)
  const [selectedVectorEngine, setSelectedVectorEngine] = useRecoilState(selectedVectorEngineState)
  const [submitDisabled, setSubmitDisabled] = useRecoilState(submitDisabledState)
  const [uploadedFiles, setUploadedFiles] = useRecoilState(uploadedFilesState)
  
  useEffect(() => {
    console.log('initializing:')
    console.dir(selectedVectorEngine)
    console.dir(tmpParams)
    setParams(tmpParams)
  }, [])

  useEffect(() => {
    if (params && params.id) {
      console.log('params.id: ' + params.id)
      setUrlCollectionId(params.id)
    }
  }, [params])
  
  useEffect(() => {
    (async () => {
      if (urlCollectionId) {
        // console.log("Fetching details for currentCollection " + urlCollectionId)
        let result = await api.getDocCollections()
        // console.log(`Got object data result: ${JSON.stringify(result)}`)
        for (let i = 0; i < result.length; i++) {
          let tmpCollection = result[i]
          // console.log("Got tmpCollection")
          // console.dir(tmpCollection)
          // console.log(`tmpCollection.collection_id: ${tmpCollection.collection_id} == urlCollectionId ${urlCollectionId}? ${tmpCollection.collection_id === urlCollectionId}`)
          // console.log(`does collection_id ${currentCollection.collection_id} === urlCollectionId ${urlCollectionId}?`)
          if (tmpCollection.collection_id === urlCollectionId) {
            let tmpCollectionObj = new DocumentCollection(
              tmpCollection.collection_name,
              tmpCollection.description,
              tmpCollection.collection_id,
              tmpCollection.vector_db_type,
              tmpCollection.enrichment_pipelines,
              tmpCollection.shared_with,
              tmpCollection.created_date,
              tmpCollection.updated_date,
            ) 
            console.log("Converted to DocumentCollection:")
            console.dir(tmpCollectionObj)
            console.log(`Got match for collection ${tmpCollectionObj.json()}}`)
            // setCurrentCollection(tmpCollection)
            // setCollectionName(tmpCollection.collection_name.trim());
            // setCollectionDescription(tmpCollection.description.trim());
            let sharedList = []
            tmpCollectionObj.shareList.forEach(email => {
              sharedList.push({
                "key": email
              })
            })
            setCurrentCollection(tmpCollectionObj)
            setCollectionShareList(sharedList)
            console.log('tmpCollectionObj.sharedList')
            console.dir(sharedList)
            console.log('tmpCollectionObj.enrichment_pipelines')
            console.dir(tmpCollectionObj.enrichmentPipelines)
            break;
          }
        }
      }
      else {
        // console.log("Collection ID is " + urlCollectionId)
      }
      setIsLoading(false)
    })()
    // console.log('selectedVectorEngine: '+ selectedVectorEngine['label']);
  }, [urlCollectionId])

  // useEffect( () => {
  //   console.log("in DocumentCollectionForm got docCollectionEnrichmentPipelines:")
  //   console.dir(currentCollection.enrichmentPipelines)
  //   let tmp = currentCollection.clone()
  //   console.log('before updating tmp')
  //   console.dir(tmp)
  //   // tmp.enrichment_pipelines = docCollectionEnrichmentPipelines
  //   console.log("after updating collection to tmp:")
  //   console.dir(tmp)
  //   console.log( `comparing to collection. Are they equal? ${currentCollection == tmp}`)
  //   console.dir(currentCollection)
  //   setCurrentCollection(tmp)
  // }, [docCollectionEnrichmentPipelines])

  // useEffect( () => {
  //   setDeleteConfirmationMessage()
  //   checkEnableSubmit()
  // }, [currentCollection.name])

  useEffect( () => {
    checkEnableSubmit()
  }, [currentCollection])

  function checkEnableSubmit() {
    if (currentCollection && currentCollection.name !== '' && 
       currentCollection.description !== '') {
      setSubmitDisabled(false);
    }
    else {
      setSubmitDisabled(true)
    }
  }

  function confirmDeleteCollection(evt) {
    // console.log(`confirming delete collection ${urlCollectionId}`)
    setConfirmationModal(
      <DeleteConfirmationModal
        message={deleteConfirmationMessage}
        deleteFn={api.deleteDocCollection}
        deleteRedirectLocation={'#/document-collections'}
        resourceId={urlCollectionId}
        visible={true}
      />
    )
    setDeleteModalVisible(true)
    // api.deleteDocCollection(evt.urlCollectionId)
  }
  
  function getLoadingPageContent() {
    return (
      <>
        <div style={{textAlign: "center"}}>
          Loading<br/>
          <Spinner size="large"/>
        </div>
      </>
    )
  }
  function getPageContent() {
    return (
      <>
        <form onSubmit={e => {
          e.preventDefault();
          sendData(e);
        }}>
        <Form className="documentCollectionForm"
          actions={
            <SpaceBetween direction="horizontal" size="xs">
              <Button href='#/document-collections' formAction="none" variant="link">
                Cancel
              </Button>
              <Button 
                formAction='submit'
                loading={isLoading}
                variant="primary"
              >Save</Button>
              <Button 
                id='confirmDeleteDocCollection'
                formAction='none'
                loading={isDeleting}
                variant="normal"
                onClick={confirmDeleteCollection}
              >Delete</Button>
            </SpaceBetween>
          }>
          <Container>
            <SpaceBetween direction="vertical" size="l">
              {!urlCollectionId ?
              <FormField label="Collection Name">
              <Input
                onChange={({ detail }) => updateCurrentCollection("name", detail.value)}
                value={ currentCollection ? currentCollection.name: ''}
              />
              </FormField>
              : 
              <FormField label="Collection Name">
              <Input
                onChange={({ detail }) => updateCurrentCollection("name", detail.value)}
                value={currentCollection? currentCollection.name : ''}
                disabled
              />
              </FormField>
              }
              <FormField label="Collection Description">
              <Input
                onChange={({ detail }) => updateCurrentCollection("description", detail.value)}
                value={currentCollection ? currentCollection.description : ''}
              />
              </FormField>
              { urlCollectionId ?
                <SpaceBetween>
                <Tabs
                  tabs={[
                    {
                      label: 'Uploaded Documents',
                      id: 'uploaded-documents',
                      content: (<DocumentCollectionUploadedDocumentsTable
                          // urlCollectionId={urlCollectionId}
                        ></DocumentCollectionUploadedDocumentsTable>
                      )
                    },
                    {
                      label: 'Enrichment Pipelines',
                      id: 'enrichment-pipelines',
                      content: (<DocumentCollectionEnrichmentPipelines
                          // collection={collection}
                          // updateDocCollectionEnrichmentPipelines={updateDocCollectionEnrichmentPipelines}
                        ></DocumentCollectionEnrichmentPipelines>
                      )
                    },
                    {
                      label: 'Sharing',
                      id: 'sharing',
                      content: (<DocumentCollectionSharingList
                          // urlCollectionId={urlCollectionId}
                          // sharedWith={collectionShareList}
                        ></DocumentCollectionSharingList>
                      )
                    }
                  ]}
                /></SpaceBetween> : ''
              }
            </SpaceBetween>
          </Container>
        </Form>
      </form>
        {confirmationModal}
      </>)
  }
  async function sendData(){
    setIsLoading(true)
    // console.log("Sending data from filesVal:")
    // console.dir(filesVal)
    // console.log(`urlCollectionId = ${urlCollectionId}`)
    if (urlCollectionId !== null && filesVal.length > 0) {
      // we're uploading documents
      // console.log(`saving files ${JSON.stringify(filesVal)}`);
      setIsLoading(true)
      let result = await api.uploadFiles(urlCollectionId, filesVal);
      // console.log(`Files uploaded? ${result}`)
      if (result) {
        setFilesVal([])
        let tmpFiles = await getTableProvider(urlCollectionId, filePageSize, lastEvalKey)
        setUploadedFiles(tmpFiles['files'])
      }
      setIsLoading(false)
    }
    else {
      // console.log(`creating new collection ${currentCollection.name}`)
      const postObject = {
          "document_collection": {
            "collection_name": currentCollection.name,
            "description": currentCollection.description,
            "vector_db_type": selectedVectorEngine.value,
            "shared_with": [],
            "enrichment_pipelines": currentCollection.enrichmentPipelines
          }
      }
      if (urlCollectionId) {
        postObject.document_collection.collection_id = urlCollectionId
      }
      // console.log("Posting data");
      // console.dir(postObject);
      const result = await api.upsertDocCollection(postObject);
      // evt.preventDefault();
      // console.log("result from postData");
      // console.dir(result);
    }
    // console.log(`saving files ${JSON.stringify(filesVal)}`);
    // setIsLoading(true)
    // let result = await api.uploadFiles(urlCollectionId, filesVal);
    // // console.log("Files save result")
    // // console.dir(result)
    // setIsLoading(false)
    // setFilesVal([])
    // let tmpFiles = await getTableProvider(urlCollectionId, filePageSize, lastEvalKey)
    // setUploadedFiles(tmpFiles['files'])
    // // console.log("Redirecting to " + location.hash)
    location.hash = '#/document-collections';
  }

  async function updateCurrentCollection(key, value) {
    let tmp = {}
    if (typeof(currentCollection) == DocumentCollection) {
      tmp = currentCollection.clone()
    }
    else {
      tmp = JSON.parse(JSON.stringify(currentCollection))
    }
    tmp[key] = value
    setCurrentCollection(tmp)
  }

  // async function updateDocCollectionEnrichmentPipelines(pipelines) {
  //   let tmp = JSON.parse(JSON.stringify(currentCollection))
  //   tmp.enrichment_pipelines = pipelines
  //   setCollection(tmp)
  //   console.log("DocumentCollectionForm updating currentCollection to")
  //   console.dir(tmp)
  //   console.dir(pipelines)
  //   setDocCollectionEnrichmentPipelines(pipelines)
  // }

  async function updatePageIndex(indexNum) {
    // console.log(`updatePageIndex setting currentPageIndex to ${indexNum}`)
    let lastKey = ''
    if (indexNum > currentPageIndex) {
      // page up
    }
    else {
      // page down
    }
    setCurrentPageIndex(indexNum)
    // let tmpFiles = await getTableProvider(urlCollectionId, filePageSize, uploadedFiles.splice(-1)['file_name'])
    // // console.log("Got uploadedFiles:")
    // // console.dir(tmpFiles)
    // // console.log("Got uploadedFiles:")
    // // console.dir(uploadedFiles)
    // // console.log(`lastEval record `)
    // // console.dir(uploadedFiles['files'].splice(-1))
    // setLastEvalKey(uploadedFiles['files'].splice(-1)['file_name'])
    // setUploadedFiles(uploadedFiles['files'])
  }

  return (
    <>
      { isLoading ? getLoadingPageContent() : getPageContent() }
    </>
  );
}

export default DocumentCollectionForm;
// export const atoms = {
//   urlCollectionIdState,
//   currentCollectionState,
//   addUserModalState,
//   addUserModalVisibleState,
//   collectionIsDeletingState,
//   collectionIsLoadingState,
//   collectionShareListState,
//   confirmationModalState,
//   currentPageIndexState,
//   deleteConfirmationMessageState,
//   deleteModalVisibleState,
//   filesValState,
//   filesValIsLoadingState,
//   lastEvalKeyState,
//   paramsState,
//   selectedVectorEngineState,
//   submitDisabledState
// }

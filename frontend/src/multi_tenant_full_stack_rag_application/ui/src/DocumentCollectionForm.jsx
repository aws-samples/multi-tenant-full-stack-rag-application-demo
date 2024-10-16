//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { useEffect, useState } from 'react';
import Api from './commons/api';
import { Button, Container, Form, FormField, Header, Input, SpaceBetween, Spinner, Tabs } from '@cloudscape-design/components';
import { json, useParams } from 'react-router-dom';
import DeleteConfirmationModal from './DeleteConfirmationModal'
import DocumentCollection from './DocumentCollection'
import DocumentCollectionEnrichmentPipelines from './DocumentCollectionEnrichmentPipelines'
import DocumentCollectionSharingList from './DocumentCollectionSharingList'
import DocumentCollectionUploadedDocumentsTable from './DocumentCollectionUploadedDocumentsTable'
import { atom, useRecoilState, useRecoilValue /*useResetRecoilState,*/ } from 'recoil'


const api = new Api();


async function getTableProvider(urlCollectionId, limit=20, lastEvalKey='') {
  //// console.log("newApi:")
  //// console.dir(provider)
  if (!urlCollectionId) {
    return []
  }
  const data = await api.listUploadedFiles(urlCollectionId, limit, lastEvalKey);
  console.log("getTableProvider received data:")
  console.dir(data)
  return data;
}

const defaultEngine = "opensearch_managed"
const deleteModalMessageTemplate = `Are you sure you want to delete document collection "{currentCollection.name}?"`
const filePageSize = 20


export const currentCollectionState = atom({
  key: 'currentCollectionState',
  default: {},
})

export const urlCollectionIdState = atom({
  key: 'urlCollectionIdState',
  default: undefined,
})

const defaultDeleteConfirmationMessage = `Are you sure you want to delete this document collection?

    {currentCollection.name}
`

export const filesValState = atom({
  key: 'DocumentCollectionForm.filesValState',
  default: []
})


export const filesValIsLoadingState = atom({
  key: 'DocumentCollectionForm.filesValIsLoadingState',
  default: true
})


export const uploadedFilesState = atom({
  key: 'DocumentCollectionForm.uploadedFilesState',
  default: []
})


function DocumentCollectionForm() {
  let tmpParams = useParams()
  const [urlCollectionId, setUrlCollectionId] = useRecoilState(urlCollectionIdState)
  const [currentCollection, setCurrentCollection] = useRecoilState(currentCollectionState)
  // const [addUserModal, setAddUserModal] = useRecoilState(addUserModalState)
  // const [addUserModalVisible, setAddUserModalVisible] = useRecoilState(addUserModalVisibleState)
  // const [collectionShareList, setCollectionShareList] = useRecoilState(collectionShareListState)
  const [confirmationModal, setConfirmationModal] = useState(null)
  const [currentPageIndex, setCurrentPageIndex] = useState(0)
  const [deleteConfirmationMessage, setDeleteConfirmationMessage] = useState('')
  // const [deleteModalVisible, setDeleteModalVisible] = useRecoilState(deleteModalVisibleState)
  const [filesVal, setFilesVal] = useRecoilState(filesValState)
  const [isLoading, setIsLoading] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)
  const [lastEvalKey, setLastEvalKey] = useState(null)
  const [params, setParams] = useState({})
  // const [selectedVectorEngine, setSelectedVectorEngine] = useRecoilState(selectedVectorEngineState)
  const [submitDisabled, setSubmitDisabled] = useState(true)
  const [uploadedFiles, setUploadedFiles] = useRecoilState(uploadedFilesState)
  
  useEffect(() => {
    setParams(tmpParams)
    console.log(`tmpParams are ${JSON.stringify(tmpParams)}`)
    console.log(`urlCollectionId is ${urlCollectionId}`)
  }, [])

  useEffect(() => {
    console.log("params updated:")
    console.dir(params)
    if (params && params.id) {
      console.log('params.id: ' + params.id)
      setUrlCollectionId(params.id)
    }
  }, [params])
  
  useEffect(() => {
    (async () => {
      if (urlCollectionId !== undefined) {
        // console.log("Fetching details for currentCollection " + urlCollectionId)
        let result = await api.getDocCollections()
        console.log(`Got object data result: `)
        console.dir(result)

        for (let i = 0; i < result.length; i++) {
          let tmpCollection = result[i]
          console.log("Got tmpCollection")
          console.dir(tmpCollection)
          console.log(`enrichmentPipelines == ${JSON.stringify(tmpCollection.enrichment_pipelines)}`)
          // console.log(`tmpCollection.enrichment_pipelines.entity_extraction.enabled = ${tmpCollection.enrichment_pipelines.entity_extraction.enabled}`)
          // tmpCollection.enrichment_pipelines = tmpCollection.enrichment_pipelines.replaceAll(': True', ': true').replaceAll("'", "\"")
          // console.log(`tmpCollection.enrichment_pipelines before JSON.parse = ${tmpCollection.enrichment_pipelines}`)
          // tmpCollection.enrichment_pipelines = JSON.parse(tmpCollection.enrichment_pipelines)
          console.log(`tmpCollection.enrichment_pipelines after JSON.parse = ${JSON.stringify(tmpCollection.enrichment_pipelines)}`)
          console.log(`tmpCollection.collection_id: ${tmpCollection.collection_id} == urlCollectionId ${urlCollectionId}? ${tmpCollection.collection_id === urlCollectionId}`)
          console.log(`does collection_id ${tmpCollection.collection_id} === urlCollectionId ${urlCollectionId}?`)
          if (tmpCollection.collection_id === urlCollectionId) {
            let tmpCollectionObj = new DocumentCollection(
              tmpCollection.user_email,
              tmpCollection.collection_name,
              tmpCollection.description,
              tmpCollection.vector_db_type,
              tmpCollection.collection_id,
              tmpCollection.shared_with,
              tmpCollection.enrichment_pipelines,
              tmpCollection.graph_schema,
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
            // setCollectionShareList(sharedList)
            console.log('tmpCollectionObj')
            console.dir(tmpCollectionObj)
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

  useEffect( () => {
    // const onBeforeUnload = (ev) => {
    //   setCurrentCollection({})
    //   setUrlCollectionId(null)
    //   setCollectionShareList(null)
    //   setCurrentPageIndex(0)
    //   setLastEvalKey('')
    // };
    // window.addEventListener("beforeunload", onBeforeUnload);
    const deleteConfMsg = defaultDeleteConfirmationMessage.replace('{currentCollection.name}', currentCollection.name)
    setDeleteConfirmationMessage(deleteConfMsg)
    checkEnableSubmit()
    // return () => {
    //   window.removeEventListener("beforeunload", onBeforeUnload);
    // };
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
        deleteFn={deleteCollection}
        deleteRedirectLocation={'#/document-collections'}
        resourceId={urlCollectionId}
        visible={true}
      />
    )
    setDeleteModalVisible(true)
    // api.deleteDocCollection(evt.urlCollectionId)
  }
  
  function deleteCollection(collectionId) {
    api.deleteDocCollection(collectionId)
    setDeleteModalVisible(false)
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
            <SpaceBetween key="sb0" direction="horizontal" size="xs">
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
              >Delete document collection</Button>
            </SpaceBetween>
          }>
          <Container>
            <SpaceBetween key="sb1" direction="vertical" size="l">
              {!urlCollectionId ?
              <FormField key='collection_name' label="Collection Name">
              <Input
                key='collection_name'
                onChange={({ detail }) => updateCurrentCollection("name", detail.value)}
                value={ currentCollection ? currentCollection.name: ''}
              />
              </FormField>
              : 
              <FormField key='collection_name' label="Collection Name">
              <Input
                key='collection_name'
                onChange={({ detail }) => updateCurrentCollection("name", detail.value)}
                value={currentCollection? currentCollection.name : ''}
                disabled
              />
              </FormField>
              }
              <FormField key='collection_description' label="Collection Description">
              <Input
                key='collection_description'
                onChange={({ detail }) => updateCurrentCollection("description", detail.value)}
                value={currentCollection ? currentCollection.description : ''}
              />
              </FormField>
              { urlCollectionId ?
                <SpaceBetween key="sb2" >
                <Tabs
                  tabs={[
                    {
                      key: "uploaded-documents",
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
                      key: 'enrichment-pipelines',
                      content: (<DocumentCollectionEnrichmentPipelines
                          // collection={collection}
                          // updateDocCollectionEnrichmentPipelines={updateDocCollectionEnrichmentPipelines}
                        ></DocumentCollectionEnrichmentPipelines>
                      )
                    },
                    {
                      label: 'Sharing',
                      id: 'sharing',
                      key: 'sharing',
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
  async function sendData(evt){
    evt.preventDefault()
    // console.log("Sending data from filesVal:")
    // console.dir(filesVal)
    // console.log(`urlCollectionId = ${urlCollectionId}`)
    if (urlCollectionId !== null && filesVal.length > 0) {
      // we're uploading documents
      // console.log(`saving files ${JSON.stringify(filesVal)}`);
      setIsLoading(true)
      let result = await api.uploadFiles(urlCollectionId, filesVal);
      console.log(`Files uploaded? ${result}`)
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
            "vector_db_type": "opensearch_managed",
            "shared_with": [],
            "enrichment_pipelines": currentCollection.enrichmentPipelines
          }
      }
      if (urlCollectionId) {
        postObject.document_collection.collection_id = urlCollectionId
      }
      // console.log("Posting data");
      // console.dir(postObject);
      setIsLoading(true)
      const result = await api.upsertDocCollection(postObject);
      console.log("result from upsertDocCollection:")
      console.dir(result)
      const collectionName = Object.keys(result)[0]
      console.log(`Created collection with name ${collectionName}`)
      // console.log(`Creating collection with `)
      // console.dir(result[collectionName])
      let collection = result[collectionName]
      setCurrentCollection(new DocumentCollection(
        collection.user_email,
        collection.collection_name,
        collection.description,
        collection.vector_db_type,
        collection.collection_id,
        collection.shared_with,
        collection.enrichment_pipelines,
        collection.graph_schema,
        collection.created_date,
        collection.updated_date,
      ))
      setIsLoading(false)
      setUrlCollectionId(collection.collection_id)
      evt.preventDefault();
      location.hash = `#/document-collections/${result[collectionName]['collection_id']}/edit`;
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
    // setCurrentCollection({
    //   collection_name: '',
    //   description: ''
    // })
    // location.hash = '#/document-collections';
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


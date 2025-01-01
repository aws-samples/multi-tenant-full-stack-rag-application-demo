//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { useEffect, useState } from 'react'
import Api from './commons/api'
import { Button, Container, Form, FileUpload, Header, Input, SpaceBetween, Table } from '@cloudscape-design/components'
import { UPLOADED_DOCUMENTS_COLUMN_DEFINITIONS } from './commons/details-config'
import { atom, selector, useRecoilState, useRecoilValue} from 'recoil'
import { 
  currentCollectionState,
  filesValState,
  filesValIsLoadingState,
  uploadedFilesState,
  urlCollectionIdState,
} from './DocumentCollectionForm'
import DeleteConfirmationModal from './DeleteConfirmationModal'

const api = new Api()
const filePageSize = 20


async function getTableProvider(collectionId, limit=20, lastEvalKey='') {
  //// // console.log("newApi:")
  //// // console.dir(provider)
  const data = await api.listUploadedFiles(collectionId, limit, lastEvalKey);
  // // console.log("getTableProvider received data:")
  // // console.dir(data)
  return data;
}

function DocumentCollectionUploadedDocumentsTable() {

  const confirmationModalState = atom({
    key: 'UploadedDocumentsTable.confirmationModalState',
    default:  ''
  })

  const selectedFileUploadState = atom({
    key: 'UploadedDocumentsTable.selectedFileUploadState',
    default: ''
  })

  const [confirmationModal, setConfirmationModal] = useRecoilState(confirmationModalState)
  const currentCollection = useRecoilValue(currentCollectionState)
  const [deleteModalVisible, setDeleteModalVisible] = useState(false)
  const [filesVal, setFilesVal] = useRecoilState(filesValState)
  const [isLoading, setIsLoading] = useRecoilState(filesValIsLoadingState)
  const [lastEvalKey, setLastEvalKey] = useState(null)
  const [selectedFileUpload, setSelectedFileUpload] = useRecoilState(selectedFileUploadState)
  const [uploadedFiles, setUploadedFiles] = useRecoilState(uploadedFilesState)
  
  const deleteConfirmationMessageState = atom({
    key: 'UploadedDocumentsTable.deleteConfirmationMessageState',
    default: `Are you sure you want to delete the file ${selectedFileUpload ? selectedFileUpload['file_name'] : ''}?`
  })
  const [deleteConfirmationMessage, setDeleteConfirmationMessage] = useRecoilState(deleteConfirmationMessageState)

  const currentCollectionId = selector({
    key: 'currentCollectionId', // unique ID (with respect to other atoms/selectors)
    get: ({get}) => {
      const currentColl = get(currentCollectionState);
      return currentColl ? currentColl.collectionId : null;
    },
  });

  useEffect(() => {
    if (currentCollection.hasOwnProperty('collectionId') && 
        currentCollection.collectionId.length == 32 ) {
      (async () => {
        setIsLoading(true)
        let tmpFiles = await getTableProvider(currentCollection.collectionId, filePageSize, lastEvalKey)
        console.log("Got tmpFiles:")
        if (!tmpFiles || tmpFiles.length == 0) {
          tmpFiles = [{
            "key": "no-files-uploaded",
            "file_name": "No files uploaded yet.",
            "status": "",
            "disabled": true
          }]
        }
        else {
          console.dir(tmpFiles)
          for (let i = 0; i < tmpFiles.length; i++) {
            tmpFiles[i].key = `tmpFile_${i}`
            tmpFiles[i].onClick = async () => await api.downloadFile(
              currentCollection.collectionId, 
              tmpFiles[i].file_name
            );
          }
          setUploadedFiles(tmpFiles)
          setLastEvalKey(tmpFiles[tmpFiles.length - 1]['file_name'])
        }
        setIsLoading(false)
      })()
    }
  }, [currentCollection, lastEvalKey])

  useEffect(() => {
    // console.log("Set uploaded files to ")
    // console.dir(uploadedFiles)
    if (uploadedFiles) {
      setIsLoading(false)
    }
    // setIsLoading(false)
  }, [uploadedFiles])

  useEffect(() => {
    // console.log("Set selected file upload to ")
    // console.dir(selectedFileUpload)
    if (!selectedFileUpload) {
      setIsLoading(false)
    }
  }, [selectedFileUpload])

  useEffect(() => {
    (async () => {
      if (currentCollection && filesVal.length > 0) {
        setIsLoading(true)
        console.log('uploading files')
        let result = await api.uploadFiles(currentCollection.collectionId, filesVal);
        console.log("file upload result: ")
        console.dir(result)
        setFilesVal([])
        console.log('done uploading files.')
        let tmpFiles = await getTableProvider(currentCollection.collectionId, filePageSize, lastEvalKey)
        console.log("after filesVal, Got tmpFiles:")
        console.dir(tmpFiles)
        if (tmpFiles.length > 0) {
          setUploadedFiles(tmpFiles)
          setLastEvalKey(tmpFiles[tmpFiles.length - 1]['file_name'])
        }
        else {
          setUploadedFiles([])
        }
      }
    })()
  }, [currentCollection, filesVal])

  function confirmDeleteFile(evt) {
    // console.log('confirmDeleteFile received event')
    // console.dir(selectedFileUpload)
    // console.log(`confirming delete file ${selectedFileUpload['file_name']}`)
    setConfirmationModal(
      <DeleteConfirmationModal
        message={deleteConfirmationMessage}
        deleteFn={deleteFile}
        evt={evt}
        deleteRedirectLocation={window.location.href}
        resourceId={selectedFileUpload['file_name']}
        visible={true}
      />
    )
    setDeleteModalVisible(true)
    evt.preventDefault()
  }

  async function deleteFile(resourceId, evt) {
    await api.deleteFile(
      currentCollection.collectionId, 
      resourceId
    )
    setDeleteModalVisible(false)
    setConfirmationModal('')
    setSelectedFileUpload('')
    // setIsLoading(true)
    reloadTable(evt)
    // evt.preventDefault()
  }

  function reloadTable(evt) {
    (async () => {
      setIsLoading(true)
      let tmpFiles = await getTableProvider(currentCollection.collectionId, filePageSize, lastEvalKey)
      setUploadedFiles(tmpFiles)
      setIsLoading(false)
    })()
    // evt.preventDefault()
  }

  function checkInUploadedFiles(file) {
    console.log("Checking if file is in uploaded files:")
    console.dir(file)
    console.dir(uploadedFiles)
    for (let i = 0; i < uploadedFiles.length; i++) {
      if (uploadedFiles[i]['file_name'] == file.name) {
        return true
      }
    }
    return false
  }

  function updateFilesVal(files) {
    setIsLoading(true)
    console.log('Update files received:')
    let tmpUploadedFiles = [...uploadedFiles]
    console.dir(files)
    for (let i = 0; i < files.length; i++) {
      files[i].key = `uploaded_file ${i}`
    }
    setFilesVal(files);
    reloadTable()
    // // console.log("filesVal is now");
    // // console.dir(files)
    // setIsLoading(false)
  }

  // async function uploadFiles() {
  //   setIsLoading(true)
  //   console.log("filesVal before uploadFiles")
  //   console.dir(filesVal)
  //   let result = await api.uploadFiles(currentCollection.collectionId, filesVal);
  //   if (result) {
  //     // // console.log("uploadFiles result:")
  //     // // console.dir(result)
  //     setFilesVal([])
  //     // setUploadedFiles([])
  //     let tmpFiles = await getTableProvider(currentCollection.collectionId, filePageSize, lastEvalKey)
  //     console.log("Got tmpFiles")
  //     console.dir(tmpFiles)
  //     setUploadedFiles(tmpFiles['files'])
  //   }
  //   setIsLoading(false)
  // }

  return (
    <>
      <Table
        loadingText="Loading uploaded documents list."
        columnDefinitions={UPLOADED_DOCUMENTS_COLUMN_DEFINITIONS}
        items={uploadedFiles}
        selectionType="single"
        loading={isLoading}
        selectedItems={[selectedFileUpload]}
        onSelectionChange={({detail}) => {
          // // console.log("Selected file:")
          // // console.dir(detail.selectedItems[0])
          setSelectedFileUpload(detail.selectedItems[0])
        }}
        header={
          <Header
            actions={
              <SpaceBetween direction='horizontal' size='xs'>
                <Button formAction="none" onClick={reloadTable} iconName="refresh" variant="normal" />
                <FileUpload        
                  onChange={({detail}) => updateFilesVal(detail.value)}        
                  value={filesVal}  
                  visible={useRecoilValue(currentCollectionId)}     
                  i18nStrings={{          
                    uploadButtonText: e => e ? "Upload files" : "Upload file",          
                    dropzoneText: e => e ? "Drop files to upload"  : "Drop file to upload",          
                    removeFileAriaLabel: e => `Remove file ${e + 1}`,          
                    limitShowFewer: "Show fewer files",          
                    limitShowMore: "Show more files",         
                    errorIconAriaLabel: "Error"        
                  }}    
                  multiple     
                /> 
                {/* <Button 
                  onClick={uploadFiles}
                  disabled={filesVal.length === 0 || isLoading}
                  variant='primary'
                >
                  Upload
                </Button> */}
                <Button onClick={confirmDeleteFile} 
                  disabled={selectedFileUpload === ''}>
                  Delete file
                </Button>
              </SpaceBetween>
              
            }
          >
            Uploaded Documents 
          </Header>
        }
      ></Table>
      {confirmationModal}
    </>
  )
}

export default DocumentCollectionUploadedDocumentsTable;
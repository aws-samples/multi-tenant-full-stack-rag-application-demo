//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { useEffect, useState } from 'react'
import Api from './commons/api'
import { Button, Container, Form, FileUpload, Header, Input, SpaceBetween, Table, Pagination, Select } from '@cloudscape-design/components'
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

// Page size options for the dropdown
const pageSizeOptions = [
  { label: '10', value: 10 },
  { label: '20', value: 20 },
  { label: '50', value: 50 },
  { label: '100', value: 100 }
]


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
  const [selectedFileUpload, setSelectedFileUpload] = useRecoilState(selectedFileUploadState)
  
  // Use local state for uploaded files instead of Recoil to avoid conflicts
  const [uploadedFiles, setUploadedFiles] = useState([])
  
  // Pagination state
  const [pageSize, setPageSize] = useState(20)
  const [currentPageIndex, setCurrentPageIndex] = useState(1)
  const [hasNextPage, setHasNextPage] = useState(false)
  const [pageTokens, setPageTokens] = useState(['']) // Store tokens for each page, starting with empty string for first page
  
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

  // Pagination functions - moved before useEffect to fix hoisting issues
  async function loadPage(pageIndex) {
    if (!currentCollection.collectionId) return
    
    setIsLoading(true)
    setCurrentPageIndex(pageIndex)
    
    // Get the token for the requested page
    const token = pageTokens[pageIndex - 1] || ''
    console.log(`Loading page ${pageIndex} with token: "${token}"`)
    
    try {
      // Request one extra item to detect if there are more pages
      let tmpFiles = await getTableProvider(currentCollection.collectionId, pageSize + 1, token)
      console.log(`Got tmpFiles for page ${pageIndex}:`, tmpFiles)
      
      if (!tmpFiles || tmpFiles.length == 0) {
        tmpFiles = [{
          "key": "no-files-uploaded",
          "file_name": "No files uploaded yet.",
          "status": "",
          "disabled": true
        }]
        setHasNextPage(false)
      } else {
        console.log(`API returned ${tmpFiles.length} files, pageSize is ${pageSize}`)
        
        // Check if we got more results than pageSize (indicates more pages available)
        const hasMore = tmpFiles.length > pageSize
        
        // Limit the results to exactly pageSize for display
        if (tmpFiles.length > pageSize) {
          console.log(`API returned ${tmpFiles.length} files, showing ${pageSize}. More pages available.`)
          tmpFiles = tmpFiles.slice(0, pageSize)
        }
        
        for (let i = 0; i < tmpFiles.length; i++) {
          tmpFiles[i].key = `tmpFile_${i}`
          tmpFiles[i].onClick = async () => await api.downloadFile(
            currentCollection.collectionId, 
            tmpFiles[i].file_name
          );
        }
        
        setHasNextPage(hasMore)
        
        // Update page tokens - ensure we have the token for the next page
        if (hasMore && pageIndex >= pageTokens.length) {
          // For now, use the filename as the token since the backend expects it
          // In a proper implementation, this would be the DynamoDB LastEvaluatedKey
          const nextPageToken = tmpFiles[tmpFiles.length - 1]['file_name']
          console.log(`Adding token for page ${pageIndex + 1}: "${nextPageToken}"`)
          setPageTokens(prev => {
            const newTokens = [...prev]
            newTokens[pageIndex] = nextPageToken // Token for NEXT page
            return newTokens
          })
        }
      }
      
      console.log(`Setting uploadedFiles to ${tmpFiles.length} items`)
      setUploadedFiles(tmpFiles)
      
    } catch (error) {
      console.error('Error loading page:', error)
    } finally {
      setIsLoading(false)
    }
  }

  function handlePreviousPage() {
    if (currentPageIndex > 1) {
      loadPage(currentPageIndex - 1)
    }
  }

  function handleNextPage() {
    if (hasNextPage) {
      loadPage(currentPageIndex + 1)
    }
  }

  function handlePageSizeChange(selectedOption) {
    const newSize = selectedOption.value
    setPageSize(newSize)
    setCurrentPageIndex(1)
    setPageTokens([''])
    setHasNextPage(false)
    
    // Immediately load first page with new page size
    if (currentCollection.collectionId) {
      setIsLoading(true)
      // Request one extra item to detect if there are more pages
      getTableProvider(currentCollection.collectionId, newSize + 1, '').then(tmpFiles => {
        if (!tmpFiles || tmpFiles.length == 0) {
          tmpFiles = [{
            "key": "no-files-uploaded",
            "file_name": "No files uploaded yet.",
            "status": "",
            "disabled": true
          }]
          setHasNextPage(false)
        } else {
          console.log(`handlePageSizeChange: API returned ${tmpFiles.length} files, newSize is ${newSize}`)
          
          // Check if we got more results than newSize (indicates more pages available)
          const hasMore = tmpFiles.length > newSize
          
          // Limit the results to exactly newSize for display
          if (tmpFiles.length > newSize) {
            console.log(`handlePageSizeChange: API returned ${tmpFiles.length} files, showing ${newSize}. More pages available.`)
            tmpFiles = tmpFiles.slice(0, newSize)
          }
          
          for (let i = 0; i < tmpFiles.length; i++) {
            tmpFiles[i].key = `tmpFile_${i}`
            tmpFiles[i].onClick = async () => await api.downloadFile(
              currentCollection.collectionId, 
              tmpFiles[i].file_name
            );
          }
          
          setHasNextPage(hasMore)
          
          if (hasMore) {
            const nextPageToken = tmpFiles[tmpFiles.length - 1]['file_name']
            setPageTokens(['', nextPageToken])
          }
        }
        
        console.log(`handlePageSizeChange: Setting uploadedFiles to ${tmpFiles.length} items`)
        setUploadedFiles(tmpFiles)
        setIsLoading(false)
      }).catch(error => {
        console.error('Error loading page with new size:', error)
        setIsLoading(false)
      })
    }
  }

  // useEffects - placed after function definitions to avoid hoisting issues
  useEffect(() => {
    if (currentCollection.hasOwnProperty('collectionId') && 
        currentCollection.collectionId.length == 32 ) {
      // Reset pagination state when collection changes
      setCurrentPageIndex(1)
      setPageTokens([''])
      setHasNextPage(false)
      loadPage(1)
    }
  }, [currentCollection])

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
        // Reset pagination and reload first page after upload
        setCurrentPageIndex(1)
        setPageTokens([''])
        setHasNextPage(false)
        loadPage(1)
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
    // Reset pagination and reload first page
    setCurrentPageIndex(1)
    setPageTokens([''])
    setHasNextPage(false)
    loadPage(1)
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
        pagination={
          <Pagination
            currentPageIndex={currentPageIndex}
            pagesCount={hasNextPage ? currentPageIndex + 1 : currentPageIndex}
            onPreviousPageClick={handlePreviousPage}
            onNextPageClick={handleNextPage}
            previousPageAriaLabel="Previous page"
            nextPageAriaLabel="Next page"
            disabled={isLoading}
          />
        }
        header={
          <Header
            actions={
              <SpaceBetween direction='horizontal' size='xs'>
                <Select
                  selectedOption={pageSizeOptions.find(option => option.value === pageSize)}
                  onChange={({detail}) => handlePageSizeChange(detail.selectedOption)}
                  options={pageSizeOptions}
                  placeholder="Page size"
                />
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

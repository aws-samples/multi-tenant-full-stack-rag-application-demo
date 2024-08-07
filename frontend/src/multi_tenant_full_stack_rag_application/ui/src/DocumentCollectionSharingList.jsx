//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { useState, useEffect } from 'react'   
import Api from './commons/api'
import { Button, Container, Form, FormField, Header, Input, SpaceBetween, Table } from '@cloudscape-design/components'
import { SHARING_LIST_COLUMN_DEFINITIONS } from './commons/details-config';
import AddShareUserModal from './AddShareUserModal'
import DeleteConfirmationModal from './DeleteConfirmationModal'


const api = new Api()

// async function getTableProvider(collectionId, limit=20, lastEvalKey='') {
//     const data = await api.getShareList(collectionId, limit, lastEvalKey);
//     // console.log("getTableProvider received data:")
//     // console.dir(data)
//     return data;
// }

function DocumentCollectionSharingList(props) {
    const { collectionId } = props
    const [tableLoading, setTableLoading] = useState(true)
    const [sharedWith, setSharedWith] = useState([])
    const [selectedShareUser, setSelectedShareUser] = useState('')
    const [addUserModal, setAddUserModal] = useState('')
    const [deleteConfirmationModal, setDeleteConfirmationModal] = useState('')
    // const [addUserModalVisible, setAddUserModalVisible] = useState(false)

    useEffect(() => {
        // console.log("DocumentCollectionSharingList useEffect called.")
        setSharedWith(props.sharedWith)
    }, [props.sharedWith])

    useEffect(() => {
        setTableLoading(false)
    },[sharedWith])

    async function deleteShareUser(args) {
        let collectionId = args[0]
        let email = args[1]
        // console.log("deleteShareUser called with email: " + email)
        let result = await api.deleteShareUser(collectionId, email)
        // console.log("new sharedWith after update: "  + JSON.stringify(result))
        setSharedWith(result)
    }

    function hideAddUserModal() {
        setAddUserModal('')
    }
    
    function hideDeleteConfirmationModal() {
        setDeleteConfirmationModal('')
    }
    
    function showAddUserModal() {
        setAddUserModal(
            <AddShareUserModal
                collectionId={collectionId}
                visible={true}
            />
        )
    }

    function showDeleteConfirmationModal() {
        setDeleteConfirmationModal(
            <DeleteConfirmationModal
                deleteFn={deleteShareUser}
                deleteRedirectLocation={`#/document-collections/${collectionId}/edit`}
                message={`Are you sure you want to remove user ${selectedShareUser['key']} from share?`}
                resourceId={[collectionId, selectedShareUser['key']]}
                visible={true}
            />
        )
    }

    return (
        <>
            <Table
                loadingText="Fetching sharing list."
                loading={tableLoading}
                columnDefinitions={SHARING_LIST_COLUMN_DEFINITIONS}
                items={sharedWith}
                selectionType="single"
                selectedItems={[selectedShareUser]}
                onSelectionChange={({detail}) => {
                // console.log("Selected file:")
                // console.dir(detail.selectedItems[0])
                setSelectedShareUser(detail.selectedItems[0])
                }}
                header={
                <Header
                    actions={
                    <SpaceBetween direction='horizontal' size='xs'>
                        <Button
                        variant="primary"
                        onClick={function(evt) {
                            // console.log("Showing add user modal.")
                            showAddUserModal()
                            evt.preventDefault()
                        }} 
                        disabled={selectedShareUser !== ''}
                        >
                        Add user
                        </Button>
                        <Button 
                        onClick={function(evt) {
                            showDeleteConfirmationModal()
                            evt.preventDefault()
                        }} 
                        disabled={selectedShareUser === ''}>
                        Remove user
                        </Button>
                    </SpaceBetween>
                    }
                >
                    Shared with users:
                </Header>
                }
            ></Table>
            {addUserModal}
            {deleteConfirmationModal}
        </>
    )
}

export default DocumentCollectionSharingList
//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { useEffect, useState } from 'react'
import { Box, Button, Container, FormField, Input, Modal, SpaceBetween, Spinner } from '@cloudscape-design/components'
import Api from './commons/api';
import './addShareUserModal.css';
const api = new Api();


function AddShareUserModal(props) {
    const [submitDisabled, setSubmitDisabled] = useState(true)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [addShareUserModalVisible, setAddShareUserModalVisible] = useState(props.visible)
    const [spinnerVisibilityClass, setSpinnerVisibilityClass] = useState('spinnerHidden')
    const [userEmail, setUserEmail] = useState('')
    const [userList, setUserList] = useState(null)
    const [userListClass, setUserListClass] = useState('UserListHidden')
    const collectionId = props.collectionId

    const submit = async (evt) => {
        setIsSubmitting(true)
        let result = await api.shareWithUser(collectionId, userEmail)
        setIsSubmitting(false)
        setAddShareUserModalVisible(false)
        // location.reload()
    }

    const updateUserEmail = async (inputText) => {
        if (inputText == '') {
          return
        }
        setSpinnerVisibilityClass('spinnerVisible')
        setUserEmail(inputText)
        if (inputText.length >= 4) {
            let users = await api.userLookup(collectionId, inputText)
            // console.log('user lookup response:')
            // console.dir(users)
            let emails = []
            users.forEach(user => {
              // console.log("Got user:")
              // console.dir(user)
              emails.push(user.sort_key)
            })
            // console.log("Got emails:")
            // console.dir(emails)
            let userList = []
            emails.forEach(email => {
              userList.push(<><Button className="UserLink" key={email} variant="link" onClick={() => {
                setUserEmail(email)
                setSubmitDisabled(false)
              }}>{email}</Button><br/></>)
            })
            setUserList(userList)
            setUserListClass('UserListVisible')
        }
        else {
            setSubmitDisabled(true)
        }
        setSpinnerVisibilityClass('spinnerHidden')
    }
  
    return (
        <Modal
            visible={addShareUserModalVisible}
            onDismiss={() => setAddShareUserModalVisible(false)}
            footer={
              <Box float="right">
                <SpaceBetween direction="horizontal" size="xs">
                  <Button 
                    onClick={() => location.reload()}
                    variant="link"
                  >Cancel</Button>
                  <Button 
                    onClick={submit}
                    disabled={submitDisabled} 
                    variant="primary"
                    loading={isSubmitting}
                  >
                    Save
                  </Button>
                </SpaceBetween>
              </Box>
            }
            header='Please add the email of the user to share with'
          >
            <FormField
              label="User email"
            >
              <Input 
                type="text"
                loading
                required={true}
                placeholder="Type at least four characters for a lookup."
                value={userEmail}
                onChange={({ detail }) => {
                  updateUserEmail(detail.value)
                }}
                autoFocus={true}
              />
              <Box className={`${spinnerVisibilityClass}`}>
                <Spinner className='addUserSpinner' size="large"/>
              </Box>
              <Container
                className={userListClass}
              >
                {userList}
              </Container>
            </FormField>
        </Modal>
    )
}

export default AddShareUserModal
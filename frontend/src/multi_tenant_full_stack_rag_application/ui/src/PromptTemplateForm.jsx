//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { useEffect, useRef, useState } from 'react';
import Api from './commons/api';
import { Button, Container, Form, FormField, Header, Input, Multiselect, SpaceBetween, Textarea } from '@cloudscape-design/components';
import { useParams } from 'react-router-dom';
import DeleteConfirmationModal from './DeleteConfirmationModal'
import { atom, useRecoilState, useRecoilValue } from 'recoil'
import PromptTemplate from './PromptTemplate'
import { templatesState } from './PromptTemplatesTable'



const api = new Api();


function createLlmOptions(names) {
  let options = []
  names.forEach(name => {
    options.push({
      "label": name,
      "value": name
    })
  })
  // console.log(`createLlmOptions got names ${names} and is returning `)
  // console.dir(options)
  return options;
}


export const urlTemplateIdState = atom({
  key: 'PromptTemplateForm.urlTemplateId',
  default: null
})


const newTemplate = new PromptTemplate(
  '',
  ''
)

export const currentTemplateState = atom({
  key: 'PromptTemplateForm.currentTemplateState',
  default: newTemplate
})

export const promptTemplateIsLoadingState = atom({
  key: 'PromptTemplateForm.promptTemplateIsLoadingState',
  default: false
})

export const promptTemplateIsDeletingState = atom({
  key: 'PromptTemplateForm.promptTemplateIsDeletingState',
  default: false
})

export const confirmationModalState = atom({
  key: 'PromptTemplateForm.confirmationModalState',
  default: null
})

const defaultDeleteConfirmationMessage = `Are you sure you want to delete this prompt template?

{currentPromptTemplate.name}
`

export const deleteConfirmationMessage = atom({
  key: 'PromptTemplateForm.deleteConfirmationMessage',
  default: defaultDeleteConfirmationMessage
})

export const deleteModalVisibleState = atom({
  key: 'PromptTemplateForm.deleteModalVisibleState',
  default: false
})

export const submitDisabledState = atom({
  key: 'PromptTemplateForm.submitDisabledState',
  default: true
})

function PromptTemplateForm() {
  const params = useParams()
  const templates = useRecoilValue(templatesState)
  // const urlTemplateId = params.hasOwnProperty('id') ? params.id : null;
  const [currentTemplate, setCurrentTemplate] = useRecoilState(currentTemplateState)
  const [urlTemplateId, setUrlTemplateId] = useState('')
  const [isLoading, setIsLoading] = useRecoilState(promptTemplateIsLoadingState)
  const [llms, setLlms] = useState([]);
  const [llmDefaultParams, setLlmDefaultParams] = useState({});
  const [selectedLlms, setSelectedLlms] = useState([])
  const [deleteModalVisible, setDeleteModalVisible] = useState(false)
  const [llmsLoadingStatus, setLlmsLoadingStatus] = useState('loading')
  // const [stopSeqs, setStopSequences] = useState([])
  const [submitDisabled, setSubmitDisabled] = useState(true)
  const [deleteConfirmationMessage, setDeleteConfirmationMessage] = useState('')
  const [confirmationModal, setConfirmationModal] = useState(null)

  useEffect(() => {
    (async () => {
      if (urlTemplateId) {
        let result = await api.getPromptTemplate(urlTemplateId)
        console.log("Got result from api.getPromptTemplate:")
        console.dir(result)
        console.log(`got stop seqs ${result['stop_sequences']}`)
        console.log(`got model ids ${result['model_ids']}`)
        let template = new PromptTemplate(
          result['template_name'],
          result['template_text'],
          result['template_id'],
          Object.keys(result).includes('stop_sequences') ? 
            result['stop_sequences'] : 
            [],
          result['model_ids'],
          result['createdDate']
        )
        setCurrentTemplate(template)
        let selectedLlmOptions = createLlmOptions(result['model_ids'])
        setSelectedLlms(selectedLlmOptions)
        let response =  api.getLlms()
        setLlmDefaultParams(response['model_default_params']);
        let llmsOptions = []
        response['models'].forEach( modelId => {
          llmsOptions.push({
            label: modelId, 
            value: modelId
          });
        });
        // // console.log("Setting llmsOptions to:");
        // // console.dir(llmsOptions);
        setLlms(llmsOptions);
        setLlmsLoadingStatus('finished');
      }
    })()
  }, [urlTemplateId])

  useEffect(() => {
    setUrlTemplateId(params['id'])
  }, [params])
  
  useEffect( () => {
    setDeleteConfirmationMessage(`Are you sure you want to delete this prompt template?
      ${currentTemplate.name}
    `)
    checkEnableSubmit()
  }, [currentTemplate.name])

  useEffect(() => {
    (async () => {
      let response =  api.getLlms()
      setLlmDefaultParams(response['model_default_params']);
      let llmsOptions = []
      response['models'].forEach( modelId => {
        llmsOptions.push({
          label: modelId, 
          value: modelId
        });
      });
      // // console.log("Setting llmsOptions to:");
      // // console.dir(llmsOptions);
      setLlms(llmsOptions);
      setLlmsLoadingStatus('finished');
    })();
    // (async () => {  
    //   if (currentTemplate.templateId) {
    //     if (currentTemplate.templateId.startsWith('default_')) {
    //       window.location.href = '/#/prompt-templates'
    //     }
    //     // console.log("Fetching details for template " + templateId)
    //     let result = await api.getPromptTemplates('prompt_templates')
    //     // console.log(`Got prompt templates from server: `)
    //     // console.dir(result)
    //     let templateNames = Object.keys(result);
    //     for (let i = 0; i < templateNames.length; i++) {
    //       let template = result[templateNames[i]]
    //       // console.log(`does template_id ${template.template_id} === templateId ${templateId}?`)
    //       if (template.template_id === currentTemplate.templateId) {
    //         // console.log(`Got match for template `)
    //         // console.dir(template)
    //         let stopSeqs = []
    //         if (template.hasOwnProperty('stop_sequences')) {
    //           stopSeqs = template.stop_sequences
    //         }
    //         setCurrentTemplate(template);
    //         const selectedLlmList = createLlmOptions(template.model_ids);
    //         setSelectedLlms(selectedLlmList);
    //         // console.log(`selectedLlms is now ${selectedLlmList}`)
    //         break;
    //       }
    //     }
    //   }
    //   checkEnableSubmit()
    //   // console.log('selectedLlms: ' + selectedLlms);
    // })();
  }, [])

  useEffect( () => {
    checkEnableSubmit()
  }, [currentTemplate.text])

  useEffect( () => {
    checkEnableSubmit()
  }, [selectedLlms])

  function checkEnableSubmit() {
    if (currentTemplate.name !== '' && 
      currentTemplate.text !== '' &&
      selectedLlms.length > 0) {
      setSubmitDisabled(false);
    }
  }

  function confirmDeletePrompt(evt) {
    // console.log(`confirming delete prompt ${currentTemplate.templateId}`)
    setConfirmationModal(
      <DeleteConfirmationModal
        message={deleteConfirmationMessage}
        deleteFn={api.deletePromptTemplate}
        deleteRedirectLocation={'#/prompt-templates' }
        resourceId={currentTemplate.templateId}
        visible={true}
      />
    )
    setDeleteModalVisible(true)
  }

  async function sendData() {
    let modelIds = []
    selectedLlms.forEach(selection => {
      modelIds.push(selection.value);
    })
    let stopSeqs = []
    if (currentTemplate.stopSeqs.length > 0) {
      if (typeof currentTemplate.stopSeqs == 'string') {
        stopSeqs = currentTemplate.stopSeqs.split(',')
      }
      else stopSeqs = currentTemplate.stopSeqs
      console.log("Got stopSeqs ")
      console.dir(stopSeqs)
      // for (let i = 0; i < stopSeqs.length; i++) {
      //   stopSeqs[i] = stopSeqs[i].trim()
      // }
    }
    const postObject = {
      "prompt_template": {
        "template_name": currentTemplate.name,
        "template_text": currentTemplate.text,
        "stop_sequences": stopSeqs,
        "model_ids": modelIds
      },
    }
    if (currentTemplate.templateId) {
      postObject['prompt_template']['template_id'] = currentTemplate.templateId
    }
    setIsLoading(true)
    // console.log("Posting data");
    // console.dir(postObject);
    const result = await api.upsertPromptTemplate(postObject);
    // evt.preventDefault();
    // console.log(`result from postData:`)
    // console.dir(result)
    setIsLoading(false)
    // location.hash = '#/prompt-templates';
  }

  const updateCurrentTemplate = (field, value) => {
    let tmp = {...currentTemplate}
    if (field == 'stopSeqs') {
      let list = value.split(',')
      let stopSeqs = []
      list.forEach(item => {
        stopSeqs.push(item.trim())
      })
      tmp.stopSeqs = stopSeqs
    }
    else {
      if (['name', 'text'].includes(field)) {
        tmp[field] = value
      }
    }
    setCurrentTemplate(tmp)
  }
  // function updateSelectedLlms(llms) {
  //   // console.log("updateSelectedLlms got");
  //   // console.dir(llms);
  //   let tmpList = []
  //   llms.forEach(llm => {
  //     tmpList.push(llm.value)
  //   })
  //   setSelectedLlms(tmpList);
  //   // console.log("selected LLMs list is now: ");
  //   // console.dir(tmpList);
  //   llmDropDownRef({selectedLlmOptions: tmpList});
  // }

  return (
    <form onSubmit={e => {
      e.preventDefault();
      sendData(e);
    }}>
      <Form className="promptTemplateForm"
        actions={
          <SpaceBetween direction="horizontal" size="xs">
            <Button href='#/prompt-templates' formAction="none" variant="link">
              Cancel
            </Button>
            <Button
              variant="primary"
              loading={isLoading}
              disabled={submitDisabled}
            >Submit</Button>
            <Button 
                id='confirmDeletePrompt'
                formAction='none'
                loading={isLoading}
                variant="normal"
                onClick={confirmDeletePrompt}
              >Delete</Button>
          </SpaceBetween>
        }        >
        <Container
          header={
            <Header variant="h2">
              {currentTemplate.templateId ? "Edit" : "New"} Prompt Template
            </Header>
          }
        >
          <SpaceBetween direction="vertical" size="l">
            <FormField label="Template Name">
              <Input
                onChange={({ detail }) => updateCurrentTemplate('name', detail.value)}
                value={currentTemplate.name}
                disabled={currentTemplate.templateId}
                ariaRequired
              />
            </FormField>
            <FormField
              label="Prompt template"
            >
              <Textarea 
                onChange={({ detail }) => updateCurrentTemplate('text',detail.value)} 
                value={currentTemplate.text} 
                placeholder="This is a placeholder" 
                ariaRequired
              />
            </FormField>
            <FormField label="Please enter comma-separated stop sequences for this prompt:">
                <Input
                onChange={({ detail }) => updateCurrentTemplate('stopSeqs', detail.value)}
                value={currentTemplate.stopSeqs}
              />
            </FormField>
            <FormField label="Select LLMs this prompt  applies to:">
            <Multiselect
              className="multitenantragSelect"
              selectedOptions={selectedLlms}
              onChange={({ detail }) => {
                // console.log('got change to multiselect:');
                // console.dir(detail);
                setSelectedLlms(detail.selectedOptions);
              }}
              options={llms}
              loadingText="Loading LLMs"
              statusType={llmsLoadingStatus}
              ariaRequired
            />
            </FormField>
          </SpaceBetween>
        </Container>
      </Form>
      {confirmationModal}
      
    </form>
  );
}

export default PromptTemplateForm;


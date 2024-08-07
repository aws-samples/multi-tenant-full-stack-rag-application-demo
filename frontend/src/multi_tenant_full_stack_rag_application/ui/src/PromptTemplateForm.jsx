//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { useEffect, useRef, useState } from 'react';
import Api from './commons/api';
import { Button, Container, Form, FormField, Header, Input, Multiselect, SpaceBetween, Textarea } from '@cloudscape-design/components';
import { useParams } from 'react-router-dom';
import DeleteConfirmationModal from './DeleteConfirmationModal'


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

function PromptTemplateForm() {
  let params = useParams();
  const urlTemplateId = params.hasOwnProperty('id') ? params.id : null;
  const [isLoading, setIsLoading] = useState(false)
  const [llms, setLlms] = useState([]);
  const [llmDefaultParams, setLlmDefaultParams] = useState({});
  const [templateId] = useState(urlTemplateId);
  const [templateName, setTemplateName] = useState('');
  const [templateText, setTemplateText] = useState('');
  const [selectedLlms, setSelectedLlms] = useState([])
  const [deleteModalVisible, setDeleteModalVisible] = useState(false)
  const [llmsLoadingStatus, setLlmsLoadingStatus] = useState('loading')
  const [stopSequences, setStopSequences] = useState([])
  const [submitDisabled, setSubmitDisabled] = useState(true)
  const [deleteConfirmationMessage, setDeleteConfirmationMessage] = useState('')
  const [confirmationModal, setConfirmationModal] = useState(null)

  useEffect( () => {
    setDeleteConfirmationMessage(`Are you sure you want to delete this prompt template?
      ${templateName}
    `)
    checkEnableSubmit()
  }, [templateName])

  useEffect(() => {
    (async () => {
      let response = await api.getLlms()
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
    (async () => {  
      if (templateId) {
        if (templateId.startsWith('default_')) {
          window.location.href = '/#/prompt-templates'
        }
        // console.log("Fetching details for template " + templateId)
        let result = await api.getPromptTemplates('prompt_templates')
        // console.log(`Got prompt templates from server: `)
        // console.dir(result)
        let templateNames = Object.keys(result);
        for (let i = 0; i < templateNames.length; i++) {
          let template = result[templateNames[i]]
          // console.log(`does template_id ${template.template_id} === templateId ${templateId}?`)
          if (template.template_id === templateId) {
            // console.log(`Got match for template `)
            // console.dir(template)
            let stopSeqs = []
            if (template.hasOwnProperty('stop_sequences')) {
              stopSeqs = template.stop_sequences
            }
            setTemplateName(template.template_name);
            setTemplateText(template.template_text);
            setStopSequences(stopSeqs.join(', '));
            const selectedLlmList = createLlmOptions(template.model_ids);
            setSelectedLlms(selectedLlmList);
            // console.log(`selectedLlms is now ${selectedLlmList}`)
            break;
          }
        }
      }
      checkEnableSubmit()
      // console.log('selectedLlms: ' + selectedLlms);
    })();
  }, [])

  useEffect( () => {
    setDeleteConfirmationMessage(`Are you sure you want to delete this prompt template?
      ${templateName}
    `)
    checkEnableSubmit()
  }, [templateName])

  useEffect( () => {
    checkEnableSubmit()
  }, [templateText])

  useEffect( () => {
    checkEnableSubmit()
  }, [selectedLlms])

  function checkEnableSubmit() {
    if (templateName !== '' && 
      templateText !== '' &&
      selectedLlms.length > 0) {
      setSubmitDisabled(false);
    }
  }

  function confirmDeletePrompt(evt) {
    // console.log(`confirming delete prompt ${templateId}`)
    setConfirmationModal(
      <DeleteConfirmationModal
        message={deleteConfirmationMessage}
        deleteFn={api.deletePromptTemplate}
        deleteRedirectLocation={'#/prompt-templates' }
        resourceId={templateId}
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
    if (stopSequences.length > 0) {
      stopSeqs = stopSequences.split(', ')
    }
    const postObject = {
      "prompt_template": {
        "template_name": templateName,
        "template_text": templateText,
        "stop_sequences": stopSeqs,
        "model_ids": modelIds
      },
    }
    if (templateId) {
      postObject['prompt_template']['template_id'] = templateId
    }
    setIsLoading(true)
    // console.log("Posting data");
    // console.dir(postObject);
    const result = await api.upsertPromptTemplate(postObject);
    // evt.preventDefault();
    // console.log(`result from postData:`)
    // console.dir(result)
    setIsLoading(false)
    location.hash = '#/prompt-templates';
  }

  function updateSelectedLlms(llms) {
    // console.log("updateSelectedLlms got");
    // console.dir(llms);
    let tmpList = []
    llms.forEach(llm => {
      tmpList.push(llm.value)
    })
    setSelectedLlms(tmpList);
    // console.log("selected LLMs list is now: ");
    // console.dir(tmpList);
    llmDropDownRef({selectedLlmOptions: tmpList});
  }

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
              {templateId ? "Edit" : "New"} Prompt Template
            </Header>
          }
        >
          <SpaceBetween direction="vertical" size="l">
            <FormField label="Template Name">
              <Input
                onChange={({ detail }) => setTemplateName(detail.value)}
                value={templateName}
                disabled={templateId}
                ariaRequired
              />
            </FormField>
            <FormField
              label="Prompt template"
            >
              <Textarea 
                onChange={({ detail }) => setTemplateText(detail.value)} 
                value={templateText} 
                placeholder="This is a placeholder" 
                ariaRequired
              />
            </FormField>
            <FormField label="Please enter comma-separated stop sequences for this prompt:">
                <Input
                onChange={({ detail }) => {
                  let list = detail.value.split(',')
                  let stopSeqs = []
                  list.forEach(item => {
                    stopSeqs.push(item.trim())
                  })
                  setStopSequences(stopSeqs.join(', '))
                }}
                value={stopSequences}
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


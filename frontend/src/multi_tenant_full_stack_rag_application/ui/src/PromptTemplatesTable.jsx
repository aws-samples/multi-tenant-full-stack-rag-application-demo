//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { useState, useEffect } from 'react';
import { PROMPT_TEMPLATES_COLUMN_DEFINITIONS } from './commons/details-config';
import { logsTableAriaLabels } from './commons/commons';
import Api from './commons/api'
import { Box, Button, ButtonDropdown, Header, SpaceBetween, Spinner, Table } from '@cloudscape-design/components';
import "./promptTemplatesTable.css"


async function getTableProvider() {
  const provider = new Api()
  //// console.log("new Api:")
  //// console.dir(provider)
  const data = await provider.getPromptTemplates();
  // console.log("table data:");
  // console.dir(data);
  let presentationData = []
  Object.keys(data).forEach(key => {
    presentationData.push(data[key])
  })
  return presentationData;
}


function PromptTemplatesTable() {
  const [promptTemplates, setPromptTemplates] = useState([]);
  const [selectedItem, setSelectedItem] = useState({});
  const [currentTemplate, setCurrentTemplate] = useState();
  const [currentTemplateContents, setCurrentTemplateContents] = useState();
  const atLeastOneSelected = selectedItem ? true :  false;
  const [tableLoadingState, setTableLoadingState] = useState(true)
  useEffect(() => {
    (async () => {
      let promptTemplates = await getTableProvider()
      // console.log("Got prompt templates from table provider:")
      // console.dir(promptTemplates)
      let tableData = []
      promptTemplates.forEach(template => {
        // console.log("got template :")
        // console.dir(template)
        let numModels = template['model_ids'].length
        let tn = template['template_name']
        let disabled = false
        if (!tn.startsWith('default_')) {
          tn = <a title={tn} href={`/#/prompt-templates/${template['template_id']}/edit`}>{tn}</a>
        }
        else {
          disabled = true
        }
        let newTemplate = {
          template_id: template['template_id'],
          template_name: tn,
          template_text:  <a title={template['template_text']}>hover to view template contents</a>,
          model_ids: <a title={template['model_ids'].join("\n")}>hover to view {numModels} model{numModels !== 1 ? 's': ''} enabled.</a>,
          disabled: disabled
        }
        // console.dir(newTemplate)
        tableData.push(newTemplate)
      })
      setPromptTemplates(tableData)
    })()
  }, [])

  useEffect(() => {
    if (promptTemplates) {
      // console.log("promptTemplates changed")
      // console.dir(promptTemplates)
      setTableLoadingState(false)
    }  }, [promptTemplates])

  function callSetFiles(event) {
    // console.log("callSetFiles got ")
    // // console.dir(event)
    setFiles(event)
  }

  function showDetails(selected) {
    // console.log("ShowDetails got selected");
    // console.dir(selected)
    setSelectedItem(selected)
    setCurrentTemplate(selected)
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
          className="promptTemplatesTable"
          loadingText="Loading prompt templates"
          loading={tableLoadingState}
          columnDefinitions={PROMPT_TEMPLATES_COLUMN_DEFINITIONS}
          wrapLines='true'
          items={promptTemplates}
          ariaLabels={logsTableAriaLabels}
          selectionType="single"
          selectedItems={[selectedItem]}
          onSelectionChange={({ detail }) =>
            showDetails(detail.selectedItems[0])
          }
          isItemDisabled={item =>{
            // console.log(`typeof item.template_name ${typeof(item.template_name)}`)
            if (typeof(item.template_name) == 'string') {
              if (item.template_name.startsWith('default_')) {
                return true
              }
            }
            else {
              // console.log("Typeof weirdness:" + typeof(item))
              // console.dir(item)
              if (item.template_name.props.title.startsWith('default_')) {
                return true
              }
              else return false
            }
          }}
          header={
            <Header
              //counter={!promptTemplatesLoading && getHeaderCounterText(promptTemplates, selectedItems)}
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <ButtonDropdown
                    items={[
                      {
                        id: "edit",
                        disabled: !currentTemplate,
                        text: "Edit or delete template",
                        href: `/#/prompt-templates/${currentTemplate ? currentTemplate.template_id : 'none'}/edit`,
                      }
                    ]}
                  >
                    Actions
                  </ButtonDropdown>
                  <Button href="/#/prompt-templates/create" variant="primary">Create new template</Button>
                  
                </SpaceBetween>
              }
            >
              Prompt Templates
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


export default PromptTemplatesTable;
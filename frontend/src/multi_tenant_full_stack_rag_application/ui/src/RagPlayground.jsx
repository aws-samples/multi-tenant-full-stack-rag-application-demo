//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { Component, useEffect, useState } from 'react';
import { Button, Container, Grid, Header, Select, Textarea } from '@cloudscape-design/components';
import Api from './commons/api';

const api = new Api();


async function getDefaultParams() {
  const data = await api.postData('/inference', {operation: "get_default_params"});
  //// console.log("default_params:");
  //// console.dir(data);
  return data;
}

function getInferencePayload(prompt, context, llmParams, selectedLlm) {
  const inputText = `
  Answer the following question from the following context.:localtion
  Question:
  ${prompt}
  Context:
  ${context}
  Answer:
  `;
  const postObj = {
    ...llmParams,
    operation: "answer",
    question: inputText,
    model_id: selectedLlm.value,
  }
  return postObj;
}

async function getLlmAnswer(infPayload) {
  // console.log("Sending inference payload:");
  // console.dir(infPayload);
  const data = await api.postData('/inference', infPayload);
  // console.log("LLM Response:");
  // console.dir(data);
  let response = JSON.parse(data.body);
  //// console.log("Got response:")
  //// console.dir(response);
  return response.answer;
}

async function getDocCollections() {
  const data = await api.getDocCollections();
  //// console.log("doc collection data:");
  //// console.dir(data);
  return data;
}


async function getLlms() {
  //// console.log("Getting LLMs:");
  const data = await api.postData('/inference', {operation: "list_fms"});
  // console.log("llms:");
  // console.dir(data);
  let body = JSON.parse(data.body)
  delete body.foundation_models['ai21.j2-mid']
  delete body.foundation_models['ai21.j2-ultra']
  data.body = JSON.stringify(body)
  // delete data.foundation_models['ai21.j2-ultra']
  return data;
}


function RagPlayground() {
  const [docCollections, setDocCollections] = useState([]);
  const [
    selectedDocCollection,
    setSelectedDocCollection
  ] = useState({"label": "select a document collection", "value": ""});
     
  const [llms, setLlms] = useState([]);
  const [
    selectedLlm,
    setSelectedLlm
  ] = useState({"label":"select an LLM", "value": ""});
  
  const [defaultParams, setDefaultParams] = useState("");
  const [llmParams, setLlmParams] = useState('');
  const [prompt, setPrompt] = useState('');
  const [vectorDbResults, setVectorDbResults] = useState('');
  const [llmOutput, setLlmOutput] = useState('');
  const [inferencePayload, setInferencePayload] = useState('');


  useEffect(() => {
    //load doc collections drop-down
    (async () => {
      const docCollectionsTmp = await getDocCollections();
      let docCollectionsOptions = []
      docCollectionsTmp.forEach( collection => {
        docCollectionsOptions.push({
          label: collection.collection_name, 
          value: collection.collection_id
        });
      });
      //// console.log("Setting docCollectionsOptions to:");
      //// console.dir(docCollectionsOptions);
      setDocCollections(docCollectionsOptions);
      //// console.log("Loaded doc collections:");
      //// console.dir(docCollections)
    })()
  },[]);

  useEffect(() => {
    //load llms drop-down
    (async () => {
      const response = await getLlms();
      let llmsTmp = JSON.parse(response.body)['foundation_models'];
      let llmsOptions = []
      Object.keys(llmsTmp).forEach( modelId => {
        llmsOptions.push({
          label: modelId, 
          value: modelId
        });
      });
      //// console.log("Setting llmsOptions to:");
      //// console.dir(llmsOptions);
      setLlms(llmsOptions);
      //// console.log("Loaded doc collections:");
      //// console.dir(llms)
    })()

  },[])

  useEffect(() => {
    (async () => {
      const response = await getDefaultParams();
      // console.log("Response from getDefaultParams:");
      // console.dir(response.body);
      // console.log(typeof(response.body))
      let body = JSON.parse(response.body);
      // console.dir(body);
      setDefaultParams(body['default_params']);
      // console.log("defaultParams:");
      // console.dir(defaultParams);
    })()
  },[])

  async function ragSearch() {
    //// console.log("Searching vector database...");
    setVectorDbResults('please wait...');
    setLlmOutput('please wait...');
    setInferencePayload('please wait...');

    const postData = {
      operation: "search",
      top_x_per_chunk: 5,
      page_text: prompt,
      page_title: prompt,
      collection_id: selectedDocCollection.value
    }
    //// console.log("Sending this data for inference:");
    //// console.dir(postData);
    const data = await api.postData('/inference', postData);
    //// console.log("rag response:");
    const ragResponse = JSON.parse(data.body)
    //// console.log("RAG RESPONSE:");
    //// console.dir(ragResponse);
    let ragResults = ragResponse[prompt.toLowerCase()]
    //// console.log("RAG RESULTS:");
    //// console.dir(ragResults)
    let scores = Object.keys(ragResults).reverse()
    let finalRagText = ''
    let context = ''
    scores.forEach(matchScore => {
      let match = ragResults[matchScore]
      finalRagText += '********************\n'
      finalRagText += `Score: ${matchScore}\n`;
      finalRagText += `Title: ${match.title}\n`;
      finalRagText += `Url: ${match.url}\n`;
      finalRagText += `Chunk Text: ${match.page_content}\n`;
      finalRagText += '********************\n\n';
      //// console.log("Got result:");
      //// console.dir(ragResults[matchScore])
      context += match.page_content + ' '
    })
    setVectorDbResults(finalRagText)
    const infPayload = getInferencePayload(prompt, context, JSON.parse(llmParams), selectedLlm);
    setInferencePayload(JSON.stringify(infPayload, null, 2));
    setLlmOutput(await getLlmAnswer(infPayload)); 
  }
  
  function updateSelectedLlm(evt) {
    //// console.log(`updateSelectedLlm got ${evt.value}`);
    let newParamValue;
    switch(evt.value) {
      case 'amazon.titan-tg1-large':
        newParamValue = defaultParams[evt.value]['textGenerationConfig'];
        break;
      case 'ai21.j2-mid':
      case 'ai21.j2-ultra':
      case 'anthropic.claude-instant-v1':
      case 'anthropic.claude-v1':
      case 'anthropic.claude-v2':
        newParamValue = defaultParams[evt.value]
        delete newParamValue.prompt
        break;
      default:
        break;
    }
    setLlmParams(JSON.stringify(newParamValue, null, 2));
    setSelectedLlm(evt)
    //// console.dir(evt);
  }


  return (
    <>
      <Container
      className="ragPlayground"
      header={
        <Header
          variant="h2"
          description="Send a query and get results from your vector database and the answer from the LLM, for RAG application debugging."
        >
          RAG Playground
        </Header>
      }
    >
      <Grid
        gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}
      >
        <div>
          <Select
            className="multitenantragSelect"
            selectedOption={selectedDocCollection}
            onChange={({ detail }) =>
              setSelectedDocCollection(detail.selectedOption)
            }
            options={docCollections}
          />
        </div>
        <div>
          <Select
            className="multitenantragSelect"
            selectedOption={selectedLlm}
            onChange={({ detail }) =>
              updateSelectedLlm(detail.selectedOption)
            }
            options={llms}
          />
        </div>
      </Grid>
      {/*<div className="multitenantragTextArea">
        <div className="subHeading">
          Default parameters
        </div>
        <Textarea
          onChange={({ detail }) => setDefaultParams(detail.value)}
          value={JSON.stringify(defaultParams, null, 2)}
        />
          </div>*/}
      <div className="multitenantragTextArea">
        <div className="subHeading">
          LLM Parameters
        </div>
        <Textarea
          onChange={({ detail }) => setLlmParams(detail.value)}
          value={llmParams}
        />
      </div>
      <div className="multitenantragTextArea">
        <div className="subHeading">
            Prompt
        </div>
        <Textarea
          onChange={({ detail }) => setPrompt(detail.value)}
          value={prompt}
        />
      </div>
      <Button variant="primary" onClick={ragSearch}>Submit</Button>
      <div className="multitenantragTextArea">
        <div className="subHeading">
          Vector database context results
        </div>
        <Textarea
          onChange={({ detail }) => setVectorDbResults(detail.value)}
          value={vectorDbResults}
        />
      </div>
      <div className="multitenantragTextArea">
        <div className="subHeading">
          Sent inference payload:
        </div>
        <Textarea
          onChange={({ detail }) => setInferencePayload(detail.value)}
          value={inferencePayload}
        />
      </div><div className="multitenantragTextArea">
        <div className="subHeading">
          Final LLM Output
        </div>
        <Textarea
          onChange={({ detail }) => setLlmOutput(detail.value)}
          value={llmOutput}
        />
      </div>
    </Container>
    </>
  );
}
export default RagPlayground;
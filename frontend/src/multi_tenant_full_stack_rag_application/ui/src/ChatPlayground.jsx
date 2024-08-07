//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { useEffect, useState } from 'react';
import { Container, Grid, Header, Input, Select, Toggle } from '@cloudscape-design/components';
import { MainContainer, MessageContainer, MessageHeader, MessageInput, MessageList } from "@minchat/react-chat-ui";
import Api from './commons/api';
import { v4 as uuidv4 } from 'uuid';
import ReactSlider from 'react-slider';
import sanitizeHtml from 'sanitize-html';

// import modelDefaultParams from './model_default_params.json'
import './chatPlayground.css';
// import awsExports from './aws-exports';


const api = new Api();

class messageObject {
  constructor(props) {
    this.user_chat_id = props.userChatId;
    this.metadata = props.metadata;
    this.message_id = props.messageId;
    this.human_message = props.humanMessage;
    this.ai_message = props.aiMessage;
    this.feedback = props.feedback;
    this.timestamp = props.timestamp;
    this.model = props.model;
    this.memory = props.memory;
    this.prompt_template = props.promptTemplate;
    this.document_collections = props.docCollections;
  }
}


class modelObject {
  constructor(props){ 
    this.model_id = props.modelId;
    this.endpoint = props.endpoint;
    this.model_args = props.modelArgs;
    this.agent_type = props.agentType;
  }
}

const aiUser = {
  id: 'assistant',
  name: "Assistant"
}

// async function callBrStableDiffusion(messageObj) {
//   const {...msg} = messageObj;
//   let response = api.postData('br_sdxl_image', msg);
//   if (response.status_code === 200) {
//     return response.content;
//   }
//   else {
//     console.error("Error processing feedback");
//     console.error(response);
//   }
// }


// async function callModel(messageObj) {
//   const {...msg} = messageObj;
//   const payload = {
//     messageObj: messageObj
//   }
//   let response = await api.postData('generation', payload)
//   // // console.log("callModel got response:");
//   // // console.dir(response);
//   return response;
// }


function getTextFromMessages(messages) {
  let returnText = ''
  messages.forEach(msg => {
    if (returnText != '') {
      returnText += "\n"
    }
    returnText += msg.text;
  })
  return returnText;
}


// async function provideFeedback(userChatId, messageId, feedback) {
//   let postObj = {
//     "user_chat_id": userChatId,
//     "message_id": messageId,
//     "feedback": feedback
//   }
//   let response = api.postData('feedback', postObj);
//   if (response.status_code === 200) {
//     return response.content;
//   }
//   else {
//     console.error("Error processing feedback");
//     console.error(response);
//   }
// }

const initLlmValue = {"label":"select an LLM", "value": ""}
const initPromptValue = {"label": "select a prompt template", "value": ""}

function ChatPlayground(props) {
  const [docCollections, setDocCollections] = useState([]);
  const [
    selectedDocCollection,
    setSelectedDocCollection
  ] = useState({"label": "Auto: search all relevant collections", "value": ""});
  const [docCollectionsLoadingStatus, setDocCollectionsLoadingStatus] = useState('loading')
  const [llms, setLlms] = useState([]);
  const [llmsLoadingStatus, setLlmsLoadingStatus] = useState('loading') 
  const [
    selectedLlm,
    setSelectedLlm
  ] = useState(initLlmValue);
  const [currentAuth, setCurrentAuth] = useState({})
  const [currentParams, setCurrentParams] = useState(null);
  const [currentUser, setCurrentUser] = useState({});
  const [defaultParams, setDefaultParams] = useState("");
  const [enableInput, setEnableInput] = useState(false);
  const [messages, setMessages] = useState([createMessage(
    'Hello, how may I help you?',
    0,
    aiUser
  )])
  const [messageNum, setMessageNum] = useState(0);
  const [promptData, setPromptData] = useState([]);
  const [promptDataLoadingStatus, setPromptDataLoadingStatus] = useState('loading')
  const [promptOptions, setPromptOptions] = useState()
  const [selectedParamOptions, setSelectedParamOptions] = useState({})
  const [selectedPrompt, setSelectedPrompt] = useState(initPromptValue);
  const [showTypingIndicator, setShowTypingIndicator] = useState(false)
  const [sessionId] = useState(uuidv4());
  const [userChatId] = useState(`${api.userId}_${sessionId}`)
  
  useEffect(() => {
    // load list of doc collections
    (async () => {
      // set up current Auth
      setCurrentAuth(await api.getCurrentAuth);
      setCurrentUser({
        id: currentAuth.userId,
        name: 'Chat User'
      })
      // load list of doc collections
      const docCollectionsTmp = await api.getDocCollections();
      let docCollectionsOptions = []
      docCollectionsTmp.forEach( collection => {
        docCollectionsOptions.push({
          label: collection.collection_name, 
          value: collection.collection_id
        });
      });
      setDocCollections(docCollectionsOptions);
      setDocCollectionsLoadingStatus('finished');
    })();
    // load list of LLMs
    (async () => {
      let response = api.getLlms()
      let modelIds = response['models'];
      // console.log("getLlms response:", JSON.stringify(response))
      setDefaultParams(response['model_default_params']);
      
      let llmsOptions = []
      modelIds.forEach( modelId => {
        if (!modelId.includes('embed')){
          llmsOptions.push({
            label: modelId, 
            value: modelId
          });
        }
      });

      setLlms(llmsOptions);
      setLlmsLoadingStatus('finished');
    })()
  }, [])
  
  useEffect(() => {
    (async () => {
        //get prompts
        const promptsResult = await api.getPromptTemplates();
        setPromptData(promptsResult);
        setPromptDataLoadingStatus('finished');
    })()
    // console.log("useEffect setting enable input to true");
  },[selectedLlm])

  useEffect(() => {
    // console.log("useEffect got currentParams");
    // console.dir(currentParams);
    if (currentParams) {
      updateParamsContent(selectedLlm.value, currentParams)
    }
    else {
      // console.log('received undefined currentParams:');
      // console.dir(currentParams)
    }
  }, [currentParams])

  useEffect(() => {
    if (selectedLlm != initLlmValue && 
       selectedPrompt != initPromptValue
    ) {
      setEnableInput(true)
      // console.log('selectedLlm is ')
      // console.dir(selectedLlm)
      // console.log(`useEffect got selectedLlm ${selectedLlm.value}`);
      let params = defaultParams[selectedLlm.value]
      // console.log(`params for selected model ${selectedLlm.value} are ${JSON.stringify(params)}`)
      params = initParams(params)
      // console.log(`after initParams, params is now ${JSON.stringify(params)}`);
      // console.dir(params);
      setCurrentParams(params)
    }
    //// console.dir(evt);
  }, [selectedLlm])

  useEffect(() => {
    // console.log(`Got selected llm ${selectedLlm.value} and prompt data ${JSON.stringify(promptData)}`)
    let options = []
    if (promptData != []) {
      promptData.forEach(promptObj => {
        if (promptObj.model_ids.includes(selectedLlm.value)) {
          options.push({
            label: promptObj.template_name,
            value: promptObj.template_id
          })
        }
      })
      if (options.length > 0) {
        setPromptOptions(options)
        setSelectedPrompt(options[0]);
      }
      else {
        setPromptOptions([])
        setSelectedPrompt({label: null, value: null})
      }
    }
  }, [promptData, selectedLlm])

  useEffect(() => {
    // console.log("Got selected prompt: ");
    // console.dir(selectedPrompt);
  }, [selectedPrompt])

  function createMessage(msgText, msgNum, user) {
    const ts = Date.now()
    return {
        text: escapeHtml(msgText), //"Hello. How can I help you?",
        messageId: msgNum,
        sentTime: ts,
        user: user
    }
  }
  
  function escapeHtml(unescapedStr) {
    return sanitizeHtml(unescapedStr);
    // return (unescapedStr.replaceAll('&', '&amp;') 
    //       .replaceAll('<', '&lt;')
    //       .replaceAll('>', '&gt;')
    //       .replaceAll('"', '&quot;')
    //       .replaceAll("'", '&#039;'));
  }
  
  function getInput(param) {
    // console.log(`getInput got ${JSON.stringify(param)}`);
    if (['stop_sequences', 'stopSequences'].includes(param.name)) {
      return ''
    }
    if (selectedLlm.value.startsWith('amazon.')) {
      if (param.type === 'json') {
        return (
          <Grid
            className="paramGrid" 
            gridDefinition={[{ colspan: 4 }, { colspan: 8 }]}
            key={param.name}
          >
            <div className="paramLabel">{param.name}</div>
            <Input 
              onChange={({ detail }) => {
                setParameter(param.name, JSON.parse(detail.value))
              }}      
              value={JSON.stringify(currentParams['textGenerationConfig'][param.name]['value'])}
              name={param.name} 
              key={param.name}    
          />
          </Grid>
        )
      }
      else if (param.type === 'string') {
        return (
          <Grid
            className="paramGrid" 
            gridDefinition={[{ colspan: 4 }, { colspan: 8 }]}
            key={param.name}
          >
            <div className="paramLabel">{param.name}</div>
            <Input 
              onChange={({ detail }) => {
                setParameter(param.name, detail.value)
              }}      
              value={currentParams['textGenerationConfig'][param.name]['value']}
              name={param.name} 
              key={param.name}    
          />
          </Grid>
        )
      }
    }
    else {
      if (param.type === 'string') {
        return (
          <Grid
            className="paramGrid" 
            gridDefinition={[{ colspan: 4 }, { colspan: 8 }]}
            key={param.name}
          >
            <div className="paramLabel">{param.name}</div>
            <Input 
              onChange={({ detail }) => {
                setParameter(param.name, detail.value)
              }}      
              value={currentParams[param.name]['value']}
              name={param.name} 
              key={param.name}    
          />
          </Grid>
        )
      }
      else if (param.type === 'json') {
        return (
          <Grid
            className="paramGrid" 
            gridDefinition={[{ colspan: 4 }, { colspan: 8 }]}
            key={param.name}
          >
            <div className="paramLabel">{param.name}</div>
            <Input 
              onChange={({ detail }) => {
                setParameter(param.name, JSON.parse(detail.value))
              }}      
              value={JSON.stringify(currentParams[param.name]['value'])}
              name={param.name} 
              key={param.name}    
          />
          </Grid>
        )
      }
    }
  }
  
  function getSelect(param) {
    return (
      <Grid
        className="paramGrid" 
        gridDefinition={[{ colspan: 4 }, { colspan: 8 }]}
        key={param.name}
      >
        <div className="paramLabel">{param.name}</div>       
        <Select 
          selectedOption={selectedParamOptions[param]}
          onChange={({ detail }) => {
            setParameter(param.name, detail.value);
            setSelectedParamOptions(param, detail.value);
          }}      
          name={param.name} 
          key={param.name}    
          options={
            param.options.forEach(optionName => {
              return {
                label: optionName,
                value: optionName
              }
            })
          }
        />
      </Grid>
    )
  }
  
  function getSlider(param) {
    // console.log(`in getSlider, currentParams = ${JSON.stringify(currentParams)}, param = ${JSON.stringify(param)}`)
    // console.log(`selectedLlm.value = ${selectedLlm.value}`)
    if (selectedLlm.value.startsWith('amazon.')) {
      return (
        <Grid
          className={`paramGrid ${param.name}`}
          gridDefinition={[{ colspan: 4 }, {colspan:1}, { colspan: 4 }, {colspan: 2}]}
          key={param.name}
        >
          <div className="paramLabel">{param.name}</div>
          <span className="sliderValue">{param.min}</span>
          <ReactSlider
            ariaLabel={param.name}
            className="horizontal-slider customSlider"
            children="never"
            trackClassName="customSlider-track"
            thumbClassName="customSlider-thumb"
            marks={false}
            value={currentParams['textGenerationConfig'][param.name]['value']}
            onChange={(value, idx) => {
              // // console.log("slider value changed:" + value)
              setParameter(param.name, value);
            }}
            key={param.name}
            name={param.name}
            defaultValue={param.default}
            max={param.max}
            min={param.min}
            renderThumb={(props, state) => <div {...props}>{state.valueNow}</div>}
            step={param.type == 'int'? 1 : 0.01}
          />
          <span className="sliderValue">{param.max}</span>
        </Grid>
      )
    }
    else {
      return (
        <Grid
          className="paramGrid" 
          gridDefinition={[{ colspan: 4 }, {colspan:1}, { colspan: 4 }, {colspan: 2}]}
          key={param.name}
        >
          <div className="paramLabel">{param.name}</div>
          <span className="sliderValue">{param.min}</span>
          <ReactSlider
            ariaLabel={param.name}
            className="horizontal-slider customSlider"
            children="never"
            trackClassName="customSlider-track"
            thumbClassName="customSlider-thumb"
            marks={false}
            value={currentParams[param.name]['value']}
            onChange={(value, idx) => {
              // // console.log("slider value changed:" + value)
              setParameter(param.name, value);
            }}
            key={param.name}
            name={param.name}
            defaultValue={param.default}
            max={param.max}
            min={param.min}
            renderThumb={(props, state) => <div {...props}>{state.valueNow}</div>}
            step={param.type == 'int'? 1 : 0.01}
          />
          <span className="sliderValue">{param.max}</span>
        </Grid>
      )
    }
  }

  function getToggle(param) {
    return (
      <Grid
        className="paramGrid" 
        gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}
      >        
        <div className="paramLabel">{param.name}</div>
        <Toggle
          key={param.name}
          name={param.name}
          checked={param.default}
          step={param.type == 'int'? 1 : 0.1}
        />
        
      </Grid>
    )
  }

  function initParams(params) {
    // console.log(`initParams received ${JSON.stringify(params)}`)
    let finalParams = {}
    let paramKeys = params.default_paths;
    for (let i = 0; i < paramKeys.length; i++) {
      let key = paramKeys[i];
      if (['stop_sequences', 'stopSequences'].includes(key)) {
        continue
      }
      let parts = key.split('.')
      let paramName = parts[0]
      let paramObj = params[paramName]
      let typeVal = paramObj['type']
      
      if (['prompt','inputText', 'name', 'messages', 'anthropic_version'].includes(key)) {
        // console.log(`Skipping key ${key}`)
        continue;
      }
      if ('textGenerationConfig' === key) {
         Object.keys(paramObj).forEach(subkey => {
          // console.log('processing subkey ', subkey)
          paramObj[subkey]['value'] = paramObj[subkey]['default']
         })
      }
      else if (['countPenalty','frequencyPenalty', 'presencePenalty']
        .includes(key)) {
          // // console.log(`found param ${key}: ${JSON.stringify(param)}`)
          paramObj['scale']['value'] = paramObj['scale']['default']
      }
      else {
         // pass
      }
      paramObj['name'] = paramName
      finalParams[paramName] = paramObj
      // console.log(`set finalParams[${key}] = ${JSON.stringify(paramObj)}`)
    }
    // console.log(`initParams returning finalParams ${JSON.stringify(finalParams)}`)
    return finalParams
  }


  async function sendChatMessage(msgText, msgNum) {
    // console.log("sendChatMessage got msgText:")
    // console.dir(msgText)
    // console.log("sendChatMessage got msgNum:")
    // console.dir(msgNum)
    setShowTypingIndicator(true)
    if (selectedPrompt == initPromptValue) {
      alert("Please select a model and a prompt template");
      return;
    }
    setMessageNum(messageNum + 1)
    
    const newMsg = createMessage(msgText, msgNum, currentUser)
    // console.log(`Got new message ${JSON.stringify(newMsg)}`)
    setMessages(messages.concat(
      [newMsg]
    ));
    // console.log("messages now:");
    // console.dir(messages);
    // console.log("CurrParams right before sending:")
    // console.dir(currentParams)
    
    let kwArgs = {}
    Object.keys(currentParams).forEach(key => {
      let param = currentParams[key]
      if (param.hasOwnProperty('value')) {
        kwArgs[key] = param.value
      }
      else {
        kwArgs[key] = param.default
      }
    })
    console
    const {...msgObj} = new messageObject({
      userChatId: userChatId,
      metadata: {},
      messageId: messageNum,
      humanMessage: msgText,
      aiMessage: '',
      feedback: {},
      timestamp: Date.now()/1000,
      model: new modelObject({
        modelId: selectedLlm.value,
        endpoint: 'Bedrock',
        modelArgs: kwArgs,
        agentType: ''
      }),
      memory: {"history": getTextFromMessages(messages)},
      promptTemplate: selectedPrompt.value,
      docCollections: [selectedDocCollection.value],
    })
    const postObject = {
      messageObj: msgObj
    }
    // // console.log("Sending postObject:");
    // // console.dir(postObject);
    const aiResponse = await api.generate(postObject);
    // let aiResponse = response['ai_message'];
    // const re = new RegExp("\<response\>(.*)\<\/response\>");
    // if (aiResponse.includes('<response>')) {
    //   aiResponse = aiResponse.match(re)[1];
    // }
    // // console.log("Got aiResponse: " + aiResponse);
    // // console.log("Before adding new message response:");
    // // console.dir(messages);
    setMessageNum(messageNum + 1)
    setMessages(messages.concat([newMsg, createMessage(aiResponse, messageNum, aiUser)]))
    setShowTypingIndicator(false)
    /*let newMessages = messages;
    newMessages.push(inputText)
    setMessages(newMessages);
    let formattedMsgs;
    newMessages.forEach(message => {
      formattedMsgs += <div className='chatMsg'>{message}</div>
    })
    setFormattedMessages(formattedMsgs);
    setCurrentChatInput('')
    // console.log("selected prompt is ", prompt)
    const prompt_name = prompt.value;
    // console.log(`sending message number ${messageNum}`);
    const modelObj = new modelObject({
      modelId: selectedLlm.value,
      endpointName: 'Bedrock',
      modelArgs: currentParams,
      agentType: ''
    })
    // console.log("ModelObj is ");
    // console.dir(modelObj);
    const message = new messageObject({
      userChatId: userChatId,
      metadata: {},
      messageId: messageNum,
      humanMessage:  currentChatInput,
      aiMessage: 'How can I help you?',
      feedback: {},
      timestamp: Date.now()/1000, //this is milliseconds but python expects seconds,
      model: modelObj,
      memory: {history: messages},
      promptTemplate: prompt_name
    })
    // console.log("Sending message:");
    // console.dir(message);
    const result = await callModel(message);*/
  }

  function setParameter(name, value) {
    let tmpParams = {...currentParams}
    // console.log("currentParams before change:");
    // console.dir(currentParams);
    if (selectedLlm.value.startsWith('amazon.')) {
      tmpParams['textGenerationConfig'][name]['value'] = value;
    }
    else if (['countPenalty','frequencyPenalty','presencePenalty'].includes(name)){
      tmpParams[name]['scale']['value'] = value;
    }
    else tmpParams[name]['value'] = value;

    setCurrentParams(tmpParams)
    // console.log("tmpParams now: ");
    // console.dir(tmpParams);
  }
  
  function setSelectedOptions(param, selectedOption) {
    let tmpSelected = {...selectedParamOptions};
    tmpSelected[param.name] = selectedOption;
    setSelectedParamOptions(tmpSelected);
  }

  // function updateSelectedLlm(selection) {
  //   // console.log(`updateSelectedLlm got ${selection}`);
  //   let params = defaultParams[selection.value]
  //   params = initParams(params)
  //   // console.log("currentParams is now ");
  //   // console.dir(params);
  //   setCurrentParams(params)
  //   updateParamsContent(selection.value, params);
  //   setSelectedLlm(selection)
  //   //// console.dir(evt);
  // }

  function updateParamsContent(modelId, currParams) {
    let paramsContent = [];
    // setCurrentParams(defaultParams[modelId])
    if (!currParams || currParams == {}) {
      currParams = defaultParams[modelId]
    }
    // console.log("currParams right before update loop:");
    // console.dir(currParams);
    const paramNames = Object.keys(currParams);
    // console.log(`Got paramNames ${JSON.stringify(paramNames)}`)

    for (let i = 0; i < paramNames.length; i++) {
      let name = paramNames[i];
      // console.log("Got param name " + name)
      if (["prompt","inputText", "messages", "anthropic_version"].includes(name)){
        continue;
      }
      let param = currParams[name]
      // console.log(`Got param ${name}:`);
      // console.dir(param);
      if (name ==='textGenerationConfig') {
        let paramKeys = Object.keys(param)
        // // console.log("Got nested param keys ");
        // // console.dir(paramKeys)
        for (let j = 0; j < paramKeys.length; j++) {
          let nestedParamName = paramKeys[j]
          // console.log("Nested param name is : ", nestedParamName);
          if (nestedParamName == "name") {
            continue;
          }
          let nestedParam = param[nestedParamName]
          // console.log("nested param is ");
          // console.dir(nestedParam);

          nestedParam.name = nestedParamName
          nestedParam.key = nestedParamName
          if (["string","json"].includes(nestedParam.type)) {
            // console.log("Creating input for nestedParamName", nestedParamName)
            paramsContent.push(getInput(nestedParam))
          }
          else {
            // console.log("Creating slider for nestedParamName", nestedParamName)
            paramsContent.push(getSlider(nestedParam))
          }
        }
      }
      else {
        if (["countPenalty", "frequencyPenalty", "presencePenalty"].includes(name)) {
          param.scale.name = name
          param.scale.key = name
          // console.log(`Getting slider for param.scale ${param.scale}`)
          paramsContent.push(getSlider(param.scale))
        }
        else {
          
          switch (param.type) {
            case 'string': 
            case 'json':
              paramsContent.push(getInput(param))
              break
            case 'boolean':
              paramsContent.push(getToggle(param))
              break
            case 'select': 
              paramsContent.push(getSelect(param))
              break
            default: 
              //ints and floats
              // console.log(`getting slider for param ${JSON.stringify(param)}`)
              paramsContent.push(getSlider(param))
              break
          }
        }
      }
    }
    props.updateSplitPanelContent('Click to adjust parameters for ' + modelId, paramsContent)
  }
  function onAttachClick(evt) {
    // console.log("onAttachClick called");
    // console.dir(evt);
    // props.updateSplitPanelContent('Click to adjust parameters for ' + selectedLlm.value, [])
  }

  return (
    <>
      <Container
        className="chatPlayground"
        header={
          <Header
            variant="h2"
            description="Test your combination of doc collection, prompt, and model, with chat history."
          >
            Chat Playground
          </Header>
        }
      >
      <Grid
        gridDefinition={[{ colspan: 4 }, { colspan: 4 },  { colspan: 4 }]}
      >
        <div>
          <Select
            className="multitenantragSelect"
            selectedOption={selectedDocCollection}
            onChange={({ detail }) =>
              setSelectedDocCollection(detail.selectedOption)
            }
            options={docCollections}
            loadingText="Loading doc collections"
            statusType={docCollectionsLoadingStatus}
            disabled
          />
        </div>
        <div>
          <Select
            className="multitenantragSelect"
            selectedOption={selectedLlm}
            onChange={({ detail }) => setSelectedLlm(detail.selectedOption)}
            options={llms}
            loadingText="Loading LLMs"
            statusType={llmsLoadingStatus}
          />
        </div>
        <div>
          <Select
            className="multitenantragSelect"
            selectedOption={selectedPrompt}
            onChange={({ detail }) =>{
              // // console.log("Selected prompt");
              // // console.dir(detail);
              setSelectedPrompt(detail.selectedOption);
            }}
            options={promptOptions}
            disabled={selectedLlm == initLlmValue}
            loadingText="Loading prompt templates"
            statusType={promptDataLoadingStatus}
          />
        </div>
      </Grid>
      <div style={{ position:"relative"}}>
      
      {enableInput ? 
      <div className='user-select-wrapper'>
        <MainContainer style={{'whiteSpace': 'preserve !important', /*'height': '60vh'*/ }}>
            <MessageContainer>
                <MessageHeader/>
                <MessageList
                    messages={messages}
                    showTypingIndicator={showTypingIndicator}
                    style={{'white-space': 'preserve !important'}}
                />
                <MessageInput 
                  placeholder="Type message here"
                  onSendMessage={sendChatMessage}
                  showAttachButton={false}
                />
            </MessageContainer>
        </MainContainer>
      </div>
      : '' }
      </div>
    </Container>
  </>
  );
}
export default ChatPlayground;
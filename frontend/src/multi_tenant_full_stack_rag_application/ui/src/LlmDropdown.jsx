//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { React, useState, useEffect } from 'react';
import { Multiselect, Select } from "@cloudscape-design/components";
import Api from './commons/api'


const provider = new Api()


function LlmDropdown(props) {
    const [llms, setLlms] = useState([]);
    const [llmDefaultParams, setLlmDefaultParams] = useState({});
    const [ selectedOptions, setSelectedOptions] = useState(
      props.hasOwnProperty('selectedLlmOptions') ? props.selectedLlmOptions : []
    );
    useEffect(() => {
      // console.log("props=");
      // console.dir(props);
      (async () => {
        const response = await getLlms();
        // // console.log("llm response: ", JSON.stringify(response))
        let llmsTmp = response['models'];
        // // console.log("llmsTmp:", JSON.stringify(llmsTmp))
        setLlmDefaultParams(response['model_default_params']);
        let llmsOptions = []
        llmsTmp.forEach( modelId => {
          llmsOptions.push({
            label: modelId, 
            value: modelId
          });
        });
        // // console.log("Setting llmsOptions to:");
        // // console.dir(llmsOptions);
        setLlms(llmsOptions);
      })()
    },[])


    return (
      <Multiselect
        className="multitenantragSelect"
        selectedOptions={selectedOptions}
        onChange={({ detail }) => {
          // console.log('got change to multiselect:');
          // console.dir(detail);
          setSelectedOptions(detail.selectedOptions);
          props.changeHandler(detail.selectedOptions);
        }}
        options={llms}
      />
    
      );

}

export default LlmDropdown;
//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { React, useState, useEffect } from 'react';
import { Select } from "@cloudscape-design/components";
import Api from './commons/api'


async function getLlms() {
  const provider = new Api()
  // console.log("new Api:")
  // console.dir(provider)
  const data = await provider.postData('/inference', {operation: "list_fms"});
  // console.log("llms:");
  // console.dir(data);
  return data;
}


function LlmDropdown() {
    const [llms, setLlms] = useState([]);
    const [
      selectedOption,
      setSelectedOption
    ] = useState({"label":"select an LLM", "value": ""});
      
    useEffect(() => {
      (async () => {
        const response = await getLlms();
        let llmsTmp = JSON.parse(response.body)['foundation_models'];
        let llmsOptions = []
        llmsTmp.forEach( llm => {
          llmsOptions.push({
            label: llm.modelId, 
            value: llm.modelId
          });
        });
        // console.log("Setting llmsOptions to:");
        // console.dir(llmsOptions);
        setLlms(llmsOptions);
        // console.log("Loaded doc collections:");
        // console.dir(llms)
      })()
    },[])


    return (
      <Select
        className="multitenantragSelect"
        selectedOption={selectedOption}
        onChange={({ detail }) =>
          setSelectedOption(detail.selectedOption)
        }
        options={llms}
      />
    
      );

}

export default LlmDropdown;
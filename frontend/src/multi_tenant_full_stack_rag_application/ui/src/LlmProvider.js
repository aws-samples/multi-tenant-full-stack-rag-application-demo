//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { React } from 'react';
import { useRecoilState} from 'recoil';
import atoms from './commons/atoms'
// const provider = new Api()


function LlmProvider() {
  const [llms, setLlms] = useRecoilState(atoms.llmsState);
  const [llmDefaultParams, setLlmDefaultParams] = useRecoilState(atoms.llmDefaultParamsState);
  const [selectedOptions, setSelectedOptions] = useRecoilState(atoms.selectedOptionsState);
  
}

//     useEffect(() => {
//       // console.log("props=");
//       // console.dir(props);
//       (async () => {
//         const response = await getLlms();
//         // // console.log("llm response: ", JSON.stringify(response))
//         let llmsTmp = response['models'];
//         // // console.log("llmsTmp:", JSON.stringify(llmsTmp))
//         setLlmDefaultParams(response['model_default_params']);
//         let llmsOptions = []
//         llmsTmp.forEach( modelId => {
//           llmsOptions.push({
//             label: modelId, 
//             value: modelId
//           });
//         });
//         // // console.log("Setting llmsOptions to:");
//         // // console.dir(llmsOptions);
//         setLlms(llmsOptions);
//       })()
//     },[])


//     return (
//       <Multiselect
//         className="multitenantragSelect"
//         selectedOptions={selectedOptions}
//         onChange={({ detail }) => {
//           // console.log('got change to multiselect:');
//           // console.dir(detail);
//           setSelectedOptions(detail.selectedOptions);
//           props.changeHandler(detail.selectedOptions);
//         }}
//         options={llms}
//       />
    
//       );

// }

// export default LlmDropdown;
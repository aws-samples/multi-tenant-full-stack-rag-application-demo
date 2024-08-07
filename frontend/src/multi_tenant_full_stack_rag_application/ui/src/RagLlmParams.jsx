//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0


import { Header, SpaceBetween, Textarea } from "@cloudscape-design/components";
import { useEffect, useState } from "react";
import Api from './commons/api';


function RagLlmParams() {
  const [value, setValue] = useState("");

  return (
    <div className="multitenantragTextArea">
    <div className="subHeading">
      LLM Parameters
    </div>
    <Textarea
      onChange={({ detail }) => setValue(detail.value)}
      value={value}
      placeholder="LLM parameters"
    />
    </div>
  );

}

export default RagLlmParams;
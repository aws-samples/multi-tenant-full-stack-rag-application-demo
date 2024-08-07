//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import Textarea from "@cloudscape-design/components/textarea";
import * as React from "react";

function RagInput() {
  const [value, setValue] = React.useState("");
  return (
    <div className="multitenantragTextArea">
    <Textarea
      onChange={({ detail }) => setValue(detail.value)}
      value={value}
      placeholder="Prompt"
    />
    </div>
  );

}

export default RagInput;
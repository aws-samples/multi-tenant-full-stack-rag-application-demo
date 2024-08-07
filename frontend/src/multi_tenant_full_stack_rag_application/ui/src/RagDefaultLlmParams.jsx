//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { Header, SpaceBetween, Textarea } from "@cloudscape-design/components";
import { useEffect, useState } from "react";
import Api from './commons/api';


async function getDefaultParams() {
    const api = new Api();
    // console.log("new Api:")
    // console.dir(api)
    const data = await api.postData('/inference', {operation: "get_default_params"});
    // console.log("default_params:");
    // console.dir(data);
    return data;
}


function RagDefaultParams() {
  const [value, setValue] = useState("");

    useEffect(() => {
      (async () => {
        const response = await getDefaultParams();
        let defaultParams = JSON.parse(response.body)['default_params'];
        // console.log("defaultParams:");
        // console.dir(defaultParams);
        setValue(JSON.stringify(defaultParams));
        // console.log("Loaded default params:");
      })()
    },[])

  return (
    <div className="multitenantragTextArea">
    <div className="subHeading">
      Default parameters
    </div>
    <Textarea
      onChange={({ detail }) => setValue(detail.value)}
      value={value}
      placeholder="Default parameters"
    />
    </div>
  );

}

export default RagDefaultParams;
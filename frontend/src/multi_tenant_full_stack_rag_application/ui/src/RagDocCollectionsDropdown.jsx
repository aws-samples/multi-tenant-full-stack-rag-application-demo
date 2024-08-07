//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { React, useState, useEffect } from 'react';
import Select from "@cloudscape-design/components/select";
import Api from './commons/api'


async function getDocCollections() {
  const api = new Api()
  // console.log("new Api:")
  // console.dir(api)
  const data = await api.getDocCollections();
  // console.log("doc collection data:");
  // console.dir(data);
  return data;
}


function RagDocCollectionsDropdown() {
    const [docCollections, setDocCollections] = useState([]);
    const [
      selectedOption,
      setSelectedOption
    ] = useState({"label":"select a document collection", "value": ""});
      
    useEffect(() => {
      (async () => {
        const docCollectionsTmp = await getDocCollections();
        let docCollectionsOptions = []
        docCollectionsTmp.forEach( collection => {
          docCollectionsOptions.push({
            label: collection.collection_name, 
            value: collection.collection_id
          });
        });
        // console.log("Setting docCollectionsOptions to:");
        // console.dir(docCollectionsOptions);
        setDocCollections(docCollectionsOptions);
        // console.log("Loaded doc collections:");
        // console.dir(docCollections)
      })()
    },[])


    return (
      <Select
      className="multitenantragSelect"
      selectedOption={selectedOption}
      onChange={({ detail }) =>
        setSelectedOption(detail.selectedOption)
      }
      options={docCollections}
    />
    
      );

}

export default RagDocCollectionsDropdown;
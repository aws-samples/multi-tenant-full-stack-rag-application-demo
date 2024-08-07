//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { Component } from 'react'
import DocumentCollectionForm from './DocumentCollectionForm';
import DocumentCollectionsTable from './DocumentCollectionsTable';
import RagPlayground from './RagPlayground';
import { HashRouter, Route, Routes} from 'react-router-dom';


class DocumentCollections extends Component {
    render() {
      return (
        <HashRouter>
          <Routes>
            <Route path='/' element={<DocumentCollectionsTable className="documentCollectionsTable"/>}/>
            <Route path='/document-collections' element={<DocumentCollectionsTable className="documentCollectionsTable"/>}/>
            <Route path='/document-collections/create' element={<DocumentCollectionForm className="documentCollectionsForm"/>}/>
            <Route path='/document-collections/:id/edit' element={<DocumentCollectionForm className="documentCollectionsForm"/>}/>
            <Route path='/rag-playground' element={<RagPlayground className="ragPlayground"/>}/>
          </Routes>
        </HashRouter>
      )
    }
}
export default DocumentCollections;
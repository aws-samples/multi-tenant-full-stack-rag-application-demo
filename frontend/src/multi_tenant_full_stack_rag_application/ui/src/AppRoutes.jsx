//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { Component } from 'react';
import ChatPlayground from './ChatPlayground';
import DocumentCollectionForm from './DocumentCollectionForm';
import DocumentCollectionsTable from './DocumentCollectionsTable';
import LogOut from './LogOut';
import PromptTemplateForm from './PromptTemplateForm'
import PromptTemplatesTable from './PromptTemplatesTable';
import { HashRouter, Route, Routes} from 'react-router-dom';


class AppRoutes extends Component {
    constructor(props) {
      super()
      this.updateSplitPanelContent = props.updateSplitPanelContent;
      this.signOut = props.signOut;
      this.render = this.render.bind(this);
    }
    render() {
      return (
        <HashRouter>
          <Routes>
            <Route path='/' element={<DocumentCollectionsTable className="documentCollectionsTable"/>}/>
            <Route path='/chat-playground' element={<ChatPlayground updateSplitPanelContent={this.updateSplitPanelContent} className="chatPlayground"/>}/>
            <Route path='/document-collections' element={<DocumentCollectionsTable className="documentCollectionsTable"/>}/>
            <Route path='/document-collections/create' element={<DocumentCollectionForm className="documentCollectionsForm"/>}/>
            <Route path='/document-collections/:id/edit' element={<DocumentCollectionForm className="documentCollectionsForm"/>}/>
            {/* <Route path='/logout' element={<LogOut signout={this.signOut}/>}/> */}
            <Route path='/prompt-templates' element={<PromptTemplatesTable className="promptTemplatesTable"/>}/>
            <Route path='/prompt-templates/create' element={<PromptTemplateForm className="promptTemplatesForm"/>}/>
            <Route path='/prompt-templates/:id/edit' element={<PromptTemplateForm className="promptTemplatesForm"/>}/>
            {/* <Route path='/rag-playground' element={<RagPlayground className="ragPlayground"/>}/> */}
          </Routes>
        </HashRouter>
      )
    }
}
export default AppRoutes;

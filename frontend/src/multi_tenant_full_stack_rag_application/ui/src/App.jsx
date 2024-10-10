// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { useRef, useState, useEffect } from 'react';
import AppRoutes from './AppRoutes';
import { AppLayout, Header, SplitPanel } from '@cloudscape-design/components';
import SideNavigation from '@cloudscape-design/components/side-navigation';
import { withAuthenticator } from '@aws-amplify/ui-react';
import { Amplify } from 'aws-amplify';
import { RecoilRoot } from 'recoil';

import awsExports from './aws-exports';
import "@cloudscape-design/global-styles/index.css";
import '@aws-amplify/ui-react/styles.css';


Amplify.configure(awsExports);
const tmpBreadcrumbs = [
    {
      text: 'Multi-tenant full-stack RAG app demo',
      href: '#',
    }
];

function App({user, signOut}) {
    let hash = window.location.hash;
    const [activeHref, setActiveHref] = useState(hash); //"#/document-collections");
    const [breadcrumbs, setBreadcrumbs] = useState(tmpBreadcrumbs);
    const [splitPanel, setSplitPanel] = useState(null);
    const [splitPanelContent, setSplitPanelContent] = useState(null);
    const [splitPanelTitle, setSplitPanelTitle] = useState(null);
    const appLayout = useRef();

    useEffect(() => {
        // // console.log(`setting up SplitPanel with ${splitPanelTitle} and ${splitPanelContent}`)
        if (splitPanelTitle && splitPanelContent) {
            setSplitPanel(<SplitPanel header={splitPanelTitle}>{splitPanelContent}</SplitPanel>)
        }
        else setSplitPanel(null)
    },[splitPanelContent, splitPanelTitle])

    useEffect(() => {
        // console.log("User is")
        // console.dir(user)
        // // console.log("In useEffect. hash is " + window.location.hash);
        if (!["#/chat-playground"].includes(window.location.hash)) {
            // // console.log("Deleting splitPanel")
            setSplitPanel(null)
            setSplitPanelTitle(null)
            setSplitPanelContent(null)
        }
        else {
            // // console.log("Adding splitpanel")
            setSplitPanel(<SplitPanel className='splitPanel' header={splitPanelTitle}>{splitPanelContent}</SplitPanel>)
        }
    },[])
    function configBreadcrumbs() {
        let hash = window.location.hash;
        let textParts = hash.slice(2).split('-')
        let text = ''
        textParts.forEach(part=> {
            if (text !== '') {
                text += ' ';
            }
            text += part.charAt(0).toUpperCase() + 
                part.slice(1)
        })
        tmpBreadcrumbs[1] = {
            text: text,
            href:hash
        }
        setBreadcrumbs(tmpBreadcrumbs);
    }

    const updateSplitPanelContent = (title, content) => {
        if (content && title) {
            // // console.log("Showing split panel content");
            setSplitPanelContent(content);
            setSplitPanelTitle(title)
        }
        else {
            // // console.log("Removing split panel");
            setSplitPanelContent(null);
            setSplitPanelTitle(null);
        }
    }

    return (
        <RecoilRoot>
            <AppLayout
                content={
                <>
                    <Header
                        variant="h4"
                    >
                        Welcome, {user.attributes.email}
                    </Header>
                    <AppRoutes signOut={signOut} updateSplitPanelContent={updateSplitPanelContent}/>
                </>
                }
                // breadcrumbs={
                // <BreadcrumbGroup 
                //     items={breadcrumbs} 
                //     expandAriaLabel="Show path" 
                //     ariaLabel="Breadcrumbs" 
                //     onFollow={event => {
                //         event.preventDefault();
                //         configBreadcrumbs()
                //     }}
                
                // />}
                navigation={<SideNavigation 
                    activeHref={activeHref}
                    onFollow={event => {
                        // // console.log("Following side navigation")
                        if (!event.detail.external) {
                            // // console.log("Setting activeHref")
                            setActiveHref(event.detail.href);
                            //configBreadcrumbs();
                            // // console.log("Setting SplitPanelContent")
                            updateSplitPanelContent(null, null)
                            //event.preventDefault();
                        }
                    }}
                    header={{ href: "/", text: `${awsExports.app_name}`}} 
                    items={[
                        // {
                        //     type: "link",
                        //     text: "Logout",
                        //     href: "#/logout"
                        // },
                        {
                            type: "section",
                            text: "Resources",
                            items: [
                                {
                                    type: "link",
                                    text: "Document Collections",
                                    href: "/#/document-collections"
                                },
                                {
                                    type: "link",
                                    text: "Prompt Templates",
                                    href: "/#/prompt-templates"
                                }      
                            ]        
                        },
                        {
                            type: "section",
                            text: "Chat",
                            items: [
                                // {
                                //     type: "link",
                                //     text: "RAG & Prompt Engineering",
                                //     href: "#/rag-playground"
                                // },
                                {
                                    type: "link",
                                    text: "Start a new conversation",
                                    href: "#/chat-playground"
                                } ,
                                // {
                                //     type: "link",
                                //     text: "Conversations",
                                //     href: "#/chat-playground/conversations"
                                // }         
                            ]        
                        },
                    ]}
                />}
                splitPanel={splitPanel}
            >
            </AppLayout>
        </RecoilRoot>
    );
}

//createRoot(document.getElementById('app')).render(<App />);

export default withAuthenticator(App, {signOut: true});
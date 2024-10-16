//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0


import { useEffect, useState } from 'react'   
import Api from './commons/api'
import { templatesState } from './PromptTemplatesTable'
import { Checkbox, Drawer, ExpandableSection, Header, RadioGroup, Table } from '@cloudscape-design/components'
import { atom, useRecoilState } from 'recoil'
import  { currentCollectionState } from './DocumentCollectionForm'
import './documentCollectionEnrichmentPipelines.css'
import awsExports from './aws-exports'


const api = new Api()


const enrichmentTableState = atom({
    key: 'DocumentCollectionEnrichmentPipelines.enrichmentTableState',
    default: []
})

const tableIsLoadingState = atom({
    key: 'DocumentCollectionEnrichmentPipelines.tableIsLoading',
    default: true
})

function DocumentCollectionEnrichmentPipelines() {
    const [currentCollection, setCurrentCollection ] = useRecoilState(currentCollectionState)
    const [enrichmentTable, setEnrichmentTable] = useRecoilState(enrichmentTableState)
    const [promptTemplates, setPromptTemplates] = useRecoilState(templatesState)
    const [promptTemplateOptions, setPromptTemplateOptions] = useState([])
    const [tableLoading, setTableLoading] = useState(true)

    useEffect(() => {
        console.log("useEffect got changed current collection. Updating table rows to ")
        console.dir(currentCollection['enrichmentPipelines'])
        updateTableRows(currentCollection['enrichmentPipelines'])
        // // console.log("currentCollection got updated:")
        // // console.dir(currentCollection)
        setTableLoading(false)
    }, [currentCollection])
    
    useEffect(() => {
        if (currentCollection && promptTemplates != {}) {
            let availableEnrichmentPipelines = JSON.parse(JSON.stringify(awsExports.enabled_enrichment_pipelines))
            console.log("availableEnrichmentPipelines initial value:")
            console.dir(availableEnrichmentPipelines)
            let currEnrichmentPipelines = currentCollection.enrichmentPipelines
  
            Object.keys(availableEnrichmentPipelines).forEach(pipelineId => {
                console.log(`Setting up available pipeline ${pipelineId}`)
                console.dir(availableEnrichmentPipelines[pipelineId])
                console.log("Collection is now:" )
                console.dir(currentCollection)
                console.log("currentCollection.enrichmentPipelines == ")
                console.dir(currEnrichmentPipelines)
                
                let enabled = false
                try {
                    enabled = currEnrichmentPipelines[pipelineId].enabled
                }
                catch {
                    // pass
                }

                let templateIdSelected = null
                try {
                    templateIdSelected = currEnrichmentPipelines[pipelineId].template_id
                }
                catch {
                    templateIdSelected = 'none'
                }

                let templateNameSelected = null
                try {
                    templateNameSelected = currEnrichmentPipelines[pipelineId].template_name
                }
                catch {
                    templateNameSelected = 'none'
                }

                availableEnrichmentPipelines[pipelineId].enabled = enabled
                availableEnrichmentPipelines[pipelineId].pipelineId = pipelineId
                availableEnrichmentPipelines[pipelineId].templateIdSelected = templateIdSelected
                availableEnrichmentPipelines[pipelineId].templateNameSelected = templateNameSelected  
            })
            console.log("updated availableEnrichmentPipelines:")
            console.dir(availableEnrichmentPipelines)
            updateTableRows(availableEnrichmentPipelines)
            // updateDocCollectionEnrichmentPipelines(availableEnrichmentPipelines)
        }
        let tmp = []
        Object.keys(promptTemplates).forEach((template_id) => {
            const item = promptTemplates[template_id]
            if (!item.template_id.startsWith('default_')) {
                tmp.push({ label: item.template_name, value: item.template_id })
            }
        })
        // // console.log("Prompt template options:")
        // // console.dir(tmp)
        setPromptTemplateOptions(tmp)
        setTableLoading(false)
    }, [currentCollection, promptTemplates])

    useEffect(() => {
        api.getPromptTemplates().then((promptTemplates) => {
            // let templates = []
            // // console.log("Prompt templates retrieved:")
            // // console.dir(promptTemplates)
            let templates = {
                'none': {
                    template_id: 'none',
                    template_name: 'none'
                }
            }
            promptTemplates.forEach((item) => {
                // // console.log(`Got template id ${item.template_id}, name ${item.template_name}`)
                // // console.dir(item)
                if (!item.template_id.startsWith('default_')) {
                    templates[item.template_id] = item
                }
            })
            setPromptTemplates(templates)
        })
    }, [])

    // // useEffect(() => {
    // //     if (currentCollection.enrichmentPipelines) {
    // //         // console.log("enrichment and enabled pipelines")
    // //         // console.dir(currentCollection.enrichmentPipelines)
    // //         // console.dir(enabledPipelines)
    // //         let tmp = {}
    // //         setEnabledPipelines(tmp)
    // //     }
    // // }, [currentCollection.enrichmentPipelines])

    // useEffect(() => {
    //     if (currentCollection && currentCollection.enrichmentPipelines) {
    //         let tmp = {}
    //         Object.keys(currentCollection.enrichmentPipelines).forEach((pipelineId) => {
    //             let item = currentCollection.enrichmentPipelines[pipelineId]
    //             tmp[item.id] = item.enabled
    //         })
    //         // setEnabledPipelines(tmp)
    //         // // console.log("currentCollection.enrichmentPipelines current value")
    //         // console.dir(currentCollection.enrichmentPipelines)
    //         // updateTableRows(currentCollection.enrichmentPipelines)
    //         setTableLoading(false)
    //     }
    // }, [currentCollection])

    function buildTemplateOptions(pipelineId, itemEnabled) {
        return (
            <Drawer>
                <ExpandableSection
                className="expandableSection"
                headerText={currentCollection.enrichmentPipelines.hasOwnProperty(pipelineId) && 
                    currentCollection.enrichmentPipelines[pipelineId].hasOwnProperty('templateNameSelected') ? 
                    currentCollection.enrichmentPipelines[pipelineId].templateNameSelected : 'none'}
                >
                <RadioGroup
                    onChange={({ detail }) => {
                        console.log("detail in radio group:")
                        console.dir(detail)
                        updatePipelineTemplate(detail.value, pipelineId, itemEnabled)
                    }}
                    value={currentCollection.enrichmentPipelines.hasOwnProperty(pipelineId) && 
                        currentCollection.enrichmentPipelines[pipelineId].hasOwnProperty('templateIdSelected') ? 
                        currentCollection.enrichmentPipelines[pipelineId].templateIdSelected : 'none'}
                    items={promptTemplateOptions}
                />
                </ExpandableSection>
          </Drawer>
        )
    }

    function updatePipelinesEnabled(pipelineEnabledCheck, pipelineRowItem) {
        console.dir(`updatePipelinesEnabled got pipelineEnabledCheck ${pipelineEnabledCheck}, pipelineRowItem:`)
        console.dir(pipelineRowItem)
        let pipelineId = pipelineRowItem.pipelineId
        let tmp = currentCollection.clone()
        console.dir(tmp)
        if (!tmp['enrichmentPipelines']) {
            console.log("No enrichment pipelines yet. setting it to blank object.")
            tmp['enrichmentPipelines'] = {}
        }
        console.log("Checkbox checked?")
        console.dir(pipelineEnabledCheck)

        tmp['enrichmentPipelines'][pipelineId] = {
            pipelineId: pipelineId,
            name: pipelineRowItem.name,
            enabled: pipelineEnabledCheck,
            templateIdSelected: pipelineRowItem.templateIdSelected,
            templateNameSelected: pipelineRowItem.templateNameSelected,
        }
        console.log("setting currentCollection to:")
        console.dir(tmp)
        setCurrentCollection(tmp)
        // let tmp = currentCollection.clone()
        // setEnrichmentTable([tmp[pipelineId]])
        // updateDocCollectionEnrichmentPipelines(tmp.enrichmentPipelines)
        // console.log("Updated pipelines:")
        // console.dir(currentCollection.enrichmentPipelines)
        // updateTableRows(currentCollection.enrichmentPipelines)
    }

    function updatePipelineTemplate(selectedValue, pipelineId, itemEnabled) {
        console.log(`Updating pipeline ${pipelineId} with template ${selectedValue}, ${itemEnabled}`)
        console.dir(currentCollection)
        let tmpCollection = currentCollection.clone()
        console.log("updatePipelineTemplate got tmpCollection");
        console.dir(tmpCollection)
        if (typeof tmpCollection['enrichmentPipelines'] == 'string') {
            console.log("Converting tmpCollection.enrichmentPipelines is a string. Convert it to an object.")
            let tmpStr = tmpCollection['enrichmentPipelines'].replaceAll("'", "\"").replaceAll(': True,', ': true,')
            console.log("tmpStr is now:")
            console.dir(tmpStr)
            tmpCollection['enrichmentPipelines'] = JSON.parse(tmpStr)
        }
        
        if (!tmpCollection.hasOwnProperty('enrichmentPipelines')) {
            tmpCollection['enrichmentPipelines'] = {}
        }
        if (!tmpCollection['enrichmentPipelines'].hasOwnProperty(pipelineId)) {
            tmpCollection['enrichmentPipelines'][pipelineId] = {}
        }      
        tmpCollection['enrichmentPipelines'][pipelineId]['templateIdSelected'] = selectedValue
        tmpCollection['enrichmentPipelines'][pipelineId]['templateNameSelected'] = promptTemplates[selectedValue]['template_name']
        if (tmpCollection['enrichmentPipelines'][pipelineId]['templateNameSelected'] != 'none') {
            tmpCollection['enrichmentPipelines'][pipelineId]['enabled'] = true
        }
        // console.log("Updated pipelines:")
        // console.dir(tmpCollection.enrichmentPipelines)
        // updateDocCollectionEnrichmentPipelines(tmpCollection.enrichmentPipelines)
        setCurrentCollection(tmpCollection)
        // updateTableRows(tmpCollection['enrichmentPipelines'])
    }

    function updateTableRows(enrichmentPipelines) {
        if (!enrichmentPipelines) {
            return
        }
        console.log("updateTableRows got enrichment pipelines")
        console.dir(enrichmentPipelines)
        let tableRows = []
        Object.keys(enrichmentPipelines).forEach(pipelineId => {
            // // console.log('pushing pipeline to table rows:')
            // // console.dir(availableEnrichmentPipelines[pipelineId])
            tableRows.push(enrichmentPipelines[pipelineId])
        })
        console.log("Setting enrichment table to rows: ")
        console.dir(tableRows)
        setEnrichmentTable(tableRows)
        // let tableRows = []
        // console.log("updateTableRows got enrichment pipelines")
        // console.dir(enrichmentPipelines)
        // // let ctr = 0
        // // Object.keys(enrichmentPipelines).forEach(pipelineId => {
        // //     let tmp = JSON.parse(JSON.stringify(enrichmentPipelines[pipelineId]))
        // //     tmp.key = ctr
        // //     tableRows.push(enrichmentPipelines[pipelineId])
        // //     ctr++
        // // })
        // // console.log("updating table rows to ")
        // // console.dir(tableRows)
        // setEnrichmentTable(tableRows)
        // // let currColl = currentCollection.clone()
        // // currColl.enrichmentPipelines = enrichmentPipelines
        // // console.log('about to setCurrentCollection to ')
        // // console.dir(currColl)
        // // setCurrentCollection(currColl)
        // // updateDocCollectionEnrichmentPipelines(currColl.enrichmentPipelines)
        // // enrichmentTable.forEach(row => {
        // //    tableRows.push({
        // //         id: pipelineId,
        // //         name: enrichmentPipelines[pipelineId].name,
        // //         enabled: enrichmentPipelines[pipelineId].enabled,
        // //         templateIdSelected: enrichmentPipelines[pipelineId].templateIdSelected,
        // //         templateNameSelected: enrichmentPipelines[pipelineId].templateNameSelected
        // //     })
        // // })
        // // // console.log('updating enrichment table with rows')
        // // // console.dir(tableRows)
        // // setEnrichmentTable(tableRows)
    }

    return (
        <>
            <Table
                className="enrichmentPipelinesTable"
                loadingText="Fetching list of enrichment pipelines."
                loading={tableLoading}
                columnDefinitions={[
                    {
                        id: 'enabled',
                        header: 'Enabled?',
                        cell: item => (
                            <Checkbox
                                checked={item.enabled}
                                onChange={(evt) => {
                                    evt.preventDefault()
                                    console.log("Checkbox changed. Row item is")
                                    console.dir(item)
                                    console.dir(evt)
                                    updatePipelinesEnabled(evt.detail.checked, item)
                                }}
                            />
                        ),
                        key: item => item.pipelineId,
                        isRowHeader: true,
                    },
                    {
                      id: 'enrichment_pipeline',
                      header: 'Enrichment Pipeline',
                      cell: item => item.name,
                      key: item => item.pipelineId,
                      isRowHeader: true,
                    },
                    {
                      id: 'prompt_template',
                      header: 'Enrichment Prompt Template',
                      cell: item => buildTemplateOptions(item.pipelineId, item.enabled),
                      isRowHeader: true,
                    }
                ]}
                items={enrichmentTable}
                header={
                    <Header>
                        Enable enrichment pipelines:
                    </Header>
                }
            ></Table>
        </>
    )
}

export default DocumentCollectionEnrichmentPipelines
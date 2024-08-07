//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import { Amplify, Auth, Storage } from 'aws-amplify';
import awsExports from '../aws-exports';
import bedrockModelParams from './bedrock_model_params.json';
import defaultPromptTemplates from './prompt_templates/prompt_templates.json';
import sanitizeHtml from 'sanitize-html';

const docsBucket = awsExports.doc_collections_bucket_name

Amplify.configure({
  ...awsExports,
  Auth: {
    identityPoolId: awsExports.aws_cognito_identity_pool_id,
    region: awsExports.aws_cognito_region,
    userPoolId: awsExports.aws_user_pools_id,
    userPoolWebClientId: awsExports.aws_user_pools_web_client_id
  },
  Storage: {
    AWSS3: {
      bucket: docsBucket,
      region: awsExports.aws_project_region,
    }
  }
});

// const apiName = 'gen-ai-accelerator';
// console.log(`loaded awsExports ${JSON.stringify(awsExports)}`)
// // console.log(docCollectionsHttpApiUrl)

const initEveryS = 10


export default class Api {
    constructor() {
      this.deleteDocCollection = this.deleteDocCollection.bind(this);
      this.deleteFile = this.deleteFile.bind(this);
      this.deletePromptTemplate = this.deletePromptTemplate.bind(this);
      this.getData = this.getData.bind(this);
      this.postData = this.postData.bind(this);
      this.getCurrentAuth = this.getCurrentAuth.bind(this);
      this.getDocCollections = this.getDocCollections.bind(this)
      this.initialize = this.initialize.bind(this)
      this.shareWithUser = this.shareWithUser.bind(this)
      this.getCurrentAuth();
      // this.getIdentityPoolToken(this.idToken)
      const tmpUrls = awsExports.api_urls
      this.apiUrls = {}
      Object.keys(tmpUrls).forEach(key => {
        this.apiUrls[key] = `${tmpUrls[key]}/${key}`
      })
      // console.log('apiUrls: ')
      // console.dir(this.apiUrls)
      this.lastInitialized = 0
      this.initialize()
    }

    async deleteDocCollection(collectionId) {
      let url = this.apiUrls['document_collections']
      let body = {"collection_id": collectionId}
      const response = await this.deleteData(url, body)
      // console.log(`Response from deleteDocCollectioncall: ${JSON.stringify(response)}`)
      // let collections = Cache.getItem('docCollections')
      let updatedCollections = await this.getDocCollections()
      // let updatedCollections = []
      // collections.forEach(coll => {
      //   if (coll.collection_id != collectionId) {
      //     updatedCollections.push(coll)
      //   }
      // })
      // Cache.setItem('docCollections', updatedCollections)
      return updatedCollections
    }
    
    async deleteData(url, data = {}) {
      if (!this.idToken) {
        await this.getCurrentAuth()
      }
      // console.log(`api.deleteData got url ${url} and data:`)
      // console.dir(data)
      // // console.log(`Got idToken ${this.idToken}`)
      // // console.log("Got queryParams:")
      // // console.dir(queryParams)
      // // console.log(`queryParams keys length: ${Object.keys(queryParams).length}`)
      
      let headers = {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${this.idToken}`
      }
      // console.log("headers:")
      // console.dir(headers)

      const response = await fetch(url, {
        method: "DELETE", // *GET, POST, PUT, DELETE, etc.
        mode: "cors", // no-cors, *cors, same-origin
        cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
        credentials: "include", // include, *same-origin, omit
        headers: headers,
        redirect: "follow", // manual, *follow, error
        referrerPolicy: "no-referrer", // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
        body: JSON.stringify(data),
      });
      // console.log(`Got ${url} response`)
      const body = response.json()
      // console.log(`Got ${url} body`)
      // console.dir(body)
      return body;
    }
    
    async deleteFile(collectionId, fileName) {
      let url = this.apiUrls['document_collections']
      url = `${url}/${collectionId}/${fileName}`
      // console.log(`deleteFile url: ${url}`)
      const response = this.deleteData(url)
      // console.log(`Response from deleteFile call:`)
      // console.dir(response)
      return response
      // const s3Key = `${collectionId}/${fileName}`
      // // console.log(`Deleting s3Key ${s3Key}`)
      // await Storage.remove(s3Key, { level: 'private' });    
    }

    async deletePromptTemplate(templateId) {
      let url = this.apiUrls['prompt_templates']
      let body = {"prompt_template": {"template_id": templateId}}
      // console.log("sending delete with payload ")
      // console.dir(body)
      const response = await this.deleteData(url, body)
      // console.log(`Response from deletePromptTemplate call: ${JSON.stringify(response)}`)
      // let templates = Cache.getItem('promptTemplates')
      let updatedTemplates = await this.getPromptTemplates()
      // Object.keys(templates).forEach(key => {
      //   template = templates[key]
      //   if (template.template_id != templateId) {
      //     updatedTemplates.push(template)
      //   }
      // })
      // Cache.setItem('promptTemplates', updatedTemplates)
      return updatedTemplates
    }

    async deleteShareUser(collectionId, email) {
      let url = this.apiUrls['sharing']
      url = `${url}/${collectionId}/${email}`
      // console.log(`deleteShareUser url: ${url}`)
      let response = await this.deleteData(url)
      // console.log(`Response from deleteShareUser call:`)
      // console.dir(response)
      return response
    }

  
    async generate(postObject) {
      let url = this.apiUrls['generation']
      // console.log(`Got api url ${url}`)
      let result = await this.postData(url, postObject)
      // console.log("generate received response from server:")
      // console.dir(result)
      // let response = result.replace('&', '&amp;').replace('<', '&lt;').replace(('>', '&gt'))
      let response = sanitizeHtml(result)
      return response
    }

    async getCurrentAuth() {
      if (!this.session) {
        this.session = await this.getSession()
        // // console.log("Got session:")
        // // console.dir(this.session)
      }
      if (!this.idToken) {
        this.idToken = this.getIdToken(this.session);
      }
      // if (!this.userId) {
      //   this.userId = this.getUserId(this.session);
      //   // // console.log("Got userId " + this.userId)
      // }
      if (!this.accessToken) {
        this.accessToken = this.getAccessToken(this.session)
      }
      this.currentAuth = {
        userId: this.userId,
        session: this.session,
        idToken: this.idToken
      }
      // // console.log('returning currentAuth')
      // // console.dir(this.currentAuth)
      return this.currentAuth
    }

    async getData(url, queryParams = {}) {  
      if (!this.idToken) {
        await this.getCurrentAuth()
      }
      // // console.log(`Got idToken ${this.idToken}`)
      // console.log(`getData got url ${url}`)
      // console.log("and queryParams:")
      // console.dir(queryParams)
      // // console.log(`queryParams keys length: ${Object.keys(queryParams).length}`)
      if (Object.keys(queryParams).length > 0) {
        url += '?'
        Object.keys(queryParams).forEach(key => {
          if (! url.endsWith('?')) {
            url += '&'
          }
          let value = encodeURIComponent(queryParams[key])
          key = encodeURIComponent(key)
          url += `${key}=${value}`
        })
      }
      // console.log(`Url after query params check: ${url}`)
      let headers = {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${this.idToken}`
      }
      // console.log("headers:")
      // console.dir(headers)

      // console.log(`About to call GET ${url}`)
      const response = await fetch(url, {
        method: "GET", // *GET, POST, PUT, DELETE, etc.
        mode: "cors", // no-cors, *cors, same-origin
        cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
        credentials: "include", // include, *same-origin, omit
        headers: headers,
        redirect: "follow", // manual, *follow, error
        referrerPolicy: "no-referrer", // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
      });
      // console.log('raw response from server to getData')
      // console.dir(response)
      let bodyStr= await response.text()
      // console.log(`bodyStr = ${bodyStr}`)
      //let body = JSON.parse(bodyStr)
      // console.dir(bodyStr)
      return bodyStr; // parses JSON response into native JavaScript objects
    }

    async getDocCollections(queryParams = {}) {
      // let collections = Cache.getItem('docCollections')
      // if (!collections) {
      let collections = []
      let url = this.apiUrls['document_collections']
      // console.log(`Got api url ${url}`);
      let collectionsStr = await this.getData(url, queryParams)
      // console.log("getDocCollections received response from server:")
      // console.dir(collectionsStr)
      let collectionsObj = JSON.parse(collectionsStr)
      Object.keys(collectionsObj).forEach(key => {
        // collectionsObj[key]['collection_name'] = key
        if (typeof(collectionsObj[key]['enrichment_pipelines']) == 'string') {
          collectionsObj[key]['enrichment_pipelines'] = JSON.parse(collectionsObj[key]['enrichment_pipelines'])
        }
        collections.push(collectionsObj[key])
      })
      return collections
    }

    async getAvailableEnrichmentPipelines() {
      // let collections = Cache.getItem('docCollections')
      // if (!collections) {
      let url = this.apiUrls['enrichment_pipelines']
      // console.log(`Got api url ${url}`);
      let enrichmentPipelines = await this.getData(url)
      if (typeof(enrichmentPipelines) == 'string') {
        enrichmentPipelines = JSON.parse(enrichmentPipelines)
      }
      // console.log("getAvailableEnrichmentPipelines received response from server:")
      // console.dir(enrichmentPipelines)
      if (typeof(enrichmentPipelines == 'string')) {
        // console.log("Before json parse " + enrichmentPipelines)
        enrichmentPipelines = JSON.parse(JSON.stringify(JSON.parse(enrichmentPipelines)))
      }
      // console.log("after JSON.parse:")
      // console.dir(enrichmentPipelines)
      return enrichmentPipelines
    }

    getLlms() {
      let models = Object.keys(bedrockModelParams)
      let modelsFinal = []
      models.forEach(model => {
        // console.log('Got model')
        // console.dir(model)
        if (!model.includes('embed')) {
          let modelIdParts = model.split(':')
          if (modelIdParts.length > 2) {
            model = model.split(':').slice(0, -1).join(':')
          }
          modelsFinal.push(model)
        }
      })
      return {
        models: modelsFinal,
        model_default_params: bedrockModelParams
      }
    }
    
    async getPromptTemplates(queryParams={}) {
      // let templates = Cache.getItem('promptTemplates')
      // if (!templates) {
      let templates = defaultPromptTemplates;

      let url = this.apiUrls['prompt_templates']
      let promptTemplatesObj = await this.getData(url, queryParams)
      // // console.log("getPromptTemplates received response from server:")
      // console.log(`typeof(promptTemplatesObj) == ${typeof(promptTemplatesObj)}`)
      if (typeof(promptTemplatesObj) == 'string') {
        promptTemplatesObj = JSON.parse(promptTemplatesObj)
      }
      // console.dir(promptTemplatesObj)
      Object.keys(promptTemplatesObj).forEach(key => {
        // console.log("Got template:")
        // console.dir(promptTemplatesObj[key])
        promptTemplatesObj[key]['template_name'] = key
        templates[key] = promptTemplatesObj[key]
      })
      // Cache.setItem('promptTemplates', templates)
      // }
      const ordered = Object.keys(templates).sort().reduce(
        (obj, key) => { 
          obj[key] = templates[key];
          obj[key]['template_name'] = key 
          return obj;
        }, 
        {}
      );
      let finalTemplates = []
      Object.keys(ordered).forEach(key => {
        // console.log("Current template:")
        // console.dir(ordered[key])
        finalTemplates.push(ordered[key])
      })
      return finalTemplates
    }
    
    getAccessToken(session) {
      return session.accessToken
    }

    getIdToken(session) {
      return session.idToken.jwtToken
    }

    async getSession() {
      return await Auth.currentSession();
    }
    
    initialize(apiUrl=null) {
        let now = Date.now()
        if (!this.initializing && (now - this.lastInitialized > initEveryS)) {
          // console.log(`initializing:  ${now}`)
          this.lastInitialized = now
          this.initializing = true;
          let skipInitialize = TextTrackCue
          if (!apiUrl) {
            apiUrl = this.apiUrls['initialization']
          }
          // console.log(`Got initialize got api url ${apiUrl}`)
          let urls = structuredClone(this.apiUrls)
          delete urls.initialization
          const body = { 
            "urls_to_init": Object.values(urls)
          }
          // console.log("Initializing urls ")
          // console.dir(urls)
          this.postData(apiUrl, body)
          this.initializing = false
          return true
        }
        
    }

    async listUploadedFiles(collectionId, limit=20, lastEvalKey='') {
      let url = this.apiUrls['document_collections']
      url += `/${collectionId}/${limit}/${lastEvalKey}`
      // console.log(`Got api url ${url}`)
      let response = await this.getData(url)
      if (typeof(response) == 'string') {
        response = JSON.parse(response)
      }
      console.log("listUploadedFiles received response from server:")
      console.dir(response)
      let filesStr = response.files
      console.log(`filesStr type ${typeof(filesStr)}`)
      console.log(filesStr)
      let filesList = JSON.parse(filesStr)
      console.dir(filesList)
      return filesList
    }
      
    async postData(url = "", data = {}) {
      // console.log(`postData received url ${url} and data ${data}`)
      if (!this.idToken) {
        await this.getCurrentAuth()
      }
      // Default options are marked with *
      let headers = {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${this.idToken}`
      }
      // // console.log("headers:")
      // // console.dir(headers)
      try {
        // console.log("Calling post with data and headers")
        // console.dir(data)
        // console.dir(headers)
        const response = await fetch(url, {
          method: "POST", // *GET, POST, PUT, DELETE, etc.
          mode: "cors", // no-cors, *cors, same-origin
          cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
          credentials: "include", // include, *same-origin, omit
          headers: headers,
          redirect: "follow", // manual, *follow, error
          referrerPolicy: "no-referrer", // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
          body: JSON.stringify(data), // body data type must match "Content-Type" header
        });
        // console.log('POST response')
        // console.dir(response)
        if (!response.ok) {
          throw Error(`Error in response: ${JSON.stringify(response)}`)
        }
        return response.json(); // parses JSON response into native JavaScript objects
      }
      catch (error) {
        // console.log("POST API ERROR:")
        // console.dir(error)
      }
    }

    async shareWithUser(collectionId, email) {
      // console.log(`shareWithUser received ${collectionId}, ${email}`)
      let url = this.apiUrls['sharing']
      const result = await this.postData(url, {
        collection_id: collectionId,
        share_with_email: email
      })
      // console.log('shareWithUser result:')
      // console.dir(result)
      return result
    }
  

    async uploadFiles(collectionId, files) {
      // console.log('UploadFiles received')
      // console.dir(files)
      files.forEach(async file => {
        const key = `${collectionId}/${file.name}`;
        // console.log(`uploading ${file.name} to s3://${docsBucket}/${key}`)
        let result = await Storage.put(key, file, {level: 'private'});
        // console.log("Upload result: ");
        // console.dir(result);
      })
      return true
   }

   async upsertDocCollection(collectionObj) {
    // console.log('upsertDocCollection received')
    // console.dir(collectionObj)
    let url = this.apiUrls['document_collections']
    const updatedCollections = await this.postData(url, collectionObj)
    // console.log('createDocCollection result:')
    // console.dir(updatedCollections)
    return updatedCollections
  }

  async upsertPromptTemplate(promptTemplateObj) {
    // console.log('upsertPromptTemplate received')
    // console.dir(promptTemplateObj)
    let url = this.apiUrls['prompt_templates']
    const updatedTemplates = await this.postData(url, promptTemplateObj)
    return updatedTemplates
  }

  async userLookup(collectionId, userPrefix, limit=20, lastEvalKey='*NONE*') {
    let url = this.apiUrls['sharing']
    url += `/${collectionId}/${userPrefix}/${limit}/${lastEvalKey}`
    // console.log(`Got api url ${url}`)
    let response = await this.getData(url)
    if (typeof(response) == String) {
        response = JSON.parse(response)
    }
    // console.log("userLookup received response from server:")
    // console.dir(response)
    return response
  }
}
class DocumentCollection {
    constructor(
        user_email,
        collection_name,
        description,
        vector_db_type='opensearch_managed',
        collection_id='',
        share_list = [],
        enrichment_pipelines={},
        graph_schema={},
        created_date=null,
        updated_date=null,
    ) {
        console.log("Creating DocumentCollection with name ")
        console.dir(collection_name)
        this.name = collection_name.trim()
        this.user_email = user_email.trim()
        this.description = description.trim()
        this.vectorDbType = vector_db_type.trim()
        this.collectionId = collection_id != '' ? collection_id.trim() : ''
        this.shareList = share_list
        this.enrichmentPipelines = enrichment_pipelines;
        this.graphSchema = graph_schema
        this.createdDate = created_date
        this.updatedDate = updated_date
        this.clone = this.clone.bind(this)
    }

    clone() {
        return new DocumentCollection(
            this.user_email,
            this.name,
            this.description,
            this.vectorDbType,
            this.collectionId,
            this.shareList,
            JSON.parse(JSON.stringify(this.enrichmentPipelines)),
            JSON.parse(JSON.stringify(this.graphSchema)),
            this.createdDate,
            this.updatedDate,
        )
    }
    
    json() {
        return {
            user_email: this.user_email,
            collection_name: this.name,
            description: this.description,
            vector_db_type: this.vectorDbType,
            collection_id: this.collectionId,
            shared_with: this.shareList,
            enrichment_pipelines: this.enrichmentPipelines,
            graph_schema: this.graphSchema,
            created_date: this.createdDate,
            updated_date: this.updatedDate,
        }
    }
}

export default DocumentCollection

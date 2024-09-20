class DocumentCollection {
    constructor(
        collection_name,
        description,
        collection_id,
        vector_db_type='opensearch_managed',
        enrichment_pipelines={},
        share_list = [],
        created_date=null,
        updated_date=null,
    ) {
        console.log("Creating DocumentCollection with name ")
        console.dir(collection_name)
        this.name = collection_name.trim()
        console.log("Creating DocumentCollection with description ")
        console.dir(description)
        this.description = description.trim()
        console.log("Creating DocumentCollection with collection_id ")
        console.dir(collection_id)
        this.collectionId = collection_id.trim();
        
        this.shareList = share_list;
        this.enrichmentPipelines = enrichment_pipelines;
        this.createdDate = created_date;
        this.updatedDate = updated_date;
        this.vectorDbType = vector_db_type;
        this.clone = this.clone.bind(this)
    }

    clone() {
        return new DocumentCollection(
            this.name,
            this.description,
            this.collectionId,
            this.vectorDbType,
            JSON.parse(JSON.stringify(this.enrichmentPipelines)),
            this.shareList,
            this.createdDate,
            this.updatedDate,
        )
    }
    
    json() {
        return {
            collection_name: this.name,
            description: this.description,
            collection_id: this.collectionId,
            vector_db_type: this.vectorDbType,
            enrichment_pipelines: this.enrichmentPipelines,
            shared_with: this.shareList,
            created_date: this.createdDate,
            updated_date: this.updatedDate,
        }
    }
}

export default DocumentCollection

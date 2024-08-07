class DocumentCollection {
    constructor(
        name,
        description,
        collectionId,
        vectorDbType='opensearch_managed',
        enrichmentPipelines={},
        shareList = [],
        createdDate=null,
        updatedDate=null,
    ) {
        this.name = name.trim()
        this.description = description.trim()
        this.shareList = shareList;
        this.collectionId = collectionId.trim();
        this.enrichmentPipelines = enrichmentPipelines;
        this.createdDate = createdDate;
        this.updatedDate = updatedDate;
        this.vectorDbType = vectorDbType;
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

class PromptTemplate {
    constructor(
        name,
        text,
        templateId=null,
        createdDate=null,
        updatedDate=null,
    ) {
        this.name = name.trim()
        this.text = text
        this.templateId = templateId;
        this.createdDate = createdDate;
        this.updatedDate = updatedDate;
        this.clone = this.clone.bind(this)
    }

    clone() {
        return PromptTemplate(
            this.name,
            this.text,
            this.templateId,
            this.createdDate,
            this.updatedDate,
        )
    }

    json() {
        return {
            name: this.name,
            text: this.text,
            template_id: this.collectionId,
            created_date: this.createdDate,
            updated_date: this.updatedDate,
        }
    }

    setSelectedLlms(llmList) {
        
    }
}

export default PromptTemplate

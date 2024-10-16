class PromptTemplate {
    constructor(
        name,
        text,
        templateId=null,
        stopSeqs=[],
        selectedLlms=[],
        createdDate=null,
        updatedDate=null,
    ) {
        this.name = name.trim()
        this.text = text
        this.templateId = templateId;
        this.stopSeqs = stopSeqs;
        this.selectedLlms = selectedLlms
        this.createdDate = createdDate;
        this.updatedDate = updatedDate;
        this.clone = this.clone.bind(this)
    }

    clone() {
        return PromptTemplate(
            this.name,
            this.text,
            this.templateId,
            this.stopSeqs,
            this.selectedLlms,
            this.createdDate,
            this.updatedDate,
        )
    }

    json() {
        return {
            name: this.name,
            text: this.text,
            template_id: this.collectionId,
            stop_seqs: this.stopSeqs,
            selected_llms: this.selectedLlms,
            created_date: this.createdDate,
            updated_date: this.updatedDate,
        }
    }
}

export default PromptTemplate

# Document URL Access Design

## Overview

Add document URL access capability to LightRAG API to enable direct access to source documents from search results.

## Design

### 1. Document Access Endpoint

Add a new endpoint to retrieve document content:

```python
@router.get("/{doc_id}")
async def get_document_content(
    doc_id: str,
    rag: LightRAG = Depends(get_rag)
) -> dict:
    """Get the content of a specific document
    
    Args:
        doc_id: Document ID to retrieve
        rag: LightRAG instance
        
    Returns:
        Dict containing document content and metadata
    """
    doc = await rag.full_docs.get_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "content": doc["content"],
        "metadata": doc.get("metadata", {})
    }
```

### 2. Response Schema Updates

Extend the DocStatusResponse model:

```python
class DocStatusResponse(BaseModel):
    id: str
    content_summary: str 
    content_length: int
    status: DocStatus
    created_at: str
    updated_at: str
    chunks_count: Optional[int] = None
    error: Optional[str] = None 
    metadata: Optional[dict[str, Any]] = None
    url: str = Field(description="URL to access the document content")

    def __init__(self, **data):
        super().__init__(**data)
        # Generate document URL
        self.url = f"/api/documents/{self.id}"
```

### 3. Query Response Format

Search results should include document URLs in the metadata:

```json
{
  "response": "Answer text...",
  "sources": [
    {
      "content": "Matching text chunk...", 
      "document": {
        "id": "doc-f7a92c",
        "url": "/api/documents/doc-f7a92c",
        "summary": "Document summary..."
      }
    }
  ]
}
```

### 4. Implementation Steps

1. Add get_document_content endpoint in document_routes.py
2. Update DocStatusResponse model to include URL generation
3. Modify query result processing to include document metadata 
4. Add URL field to document schemas
5. Update API documentation

### 5. Security Considerations

1. Rate Limiting:
   - Apply standard API rate limits to document access
   - Consider caching for frequently accessed docs

2. Access Control:
   - Use same authentication as other endpoints 
   - Validate document access permissions
   - Log document access attempts

3. Error Handling:
   - Return 404 for non-existent documents
   - Return 403 for unauthorized access
   - Handle missing content gracefully

### 6. Testing

1. Unit Tests:
   - Test URL generation
   - Verify document retrieval
   - Check error handling

2. Integration Tests: 
   - Test document flow from insertion to retrieval
   - Verify URL access in query results
   - Test rate limiting and caching

3. Load Tests:
   - Verify performance with concurrent access
   - Test caching effectiveness

GUIDES > KNOWLEDGE  

External Knowledge API Editor: Allen. Dify Technical Writer  

# Endpoint  

POST <your-endpoint>/retrieval  

## Header  

This APl is used to connect to a knowledge base that is independent of the Dify and maintained by developers. For more details, please refer to Connecting to an External Knowledge Base. You can use API-Key in the Authorization HTTP Header to verify permissions. The authentication logic is defined by you in the retrieval API, as shown below:  

Authorization: Bearer {API_KEY}  

## Request Body Elements  

The request accepts the following data in JSON format.  

The retrieval_setting property is an object containing the following keys:   


<html><body><table><tr><td>Property</td><td>Required</td><td>Type</td><td>Description</td><td>Example value</td></tr><tr><td>knowledge_id</td><td>TRUE</td><td>string</td><td>Your knowledge's unique ID</td><td>AAA-BBB-CCC</td></tr><tr><td>query</td><td>TRUE</td><td>string</td><td>User's query</td><td>What is Dify?</td></tr><tr><td>retrieval_setting</td><td>TRUE</td><td>object</td><td>Knowledge's retrieval parameters</td><td>See below</td></tr></table></body></html>  

<html><body><table><tr><td>Property</td><td>Required</td><td>Type</td><td>Description</td><td>Example value</td></tr><tr><td>top_k</td><td>TRUE</td><td>int</td><td>Maximum number ofretrievedresults</td><td>5</td></tr><tr><td>score_threshold</td><td>TRUE</td><td>float</td><td>The score limit of relevance of the result to the query scope:0~1</td><td>0.5</td></tr></table></body></html>  

## Request Syntax  

POST <your-endpoint>/retrieval HTTP/1.1
-- header
Content-Type: application/json
Authorization: Bearer your-api-key
-- data
{
    "knowledge_id": "your-knowledge-id",
    "query": "your question",
    "retrieval_setting":{
        "top_k": 2,
        "score_threshold": 0.5
    }
}

## Response Elements  

If the action is successful, the service sends back an HTTP 200 response.  

The following data is returned in JSON format by the service.  

The records property is a list object containing the following keys:   


<html><body><table><tr><td>Property</td><td>Required</td><td>Type</td><td>Description</td><td>Example value</td></tr><tr><td>records</td><td>TRUE</td><td>List[Object]</td><td>A list ofrecords from querying the knowledge base.</td><td>See below</td></tr></table></body></html>  

<html><body><table><tr><td>Property</td><td>Required</td><td>Type</td><td>Description</td><td>Example value</td></tr><tr><td>content</td><td>TRUE</td><td>string</td><td>Contains a chunk of text from a data source in the knowledge base.</td><td>Dify:The Innovation Engine for GenAl Applications</td></tr><tr><td>score</td><td>TRUE</td><td>float</td><td>The score of relevance of the result to the query. scope:0~1</td><td>0.5</td></tr><tr><td>title</td><td>TRUE</td><td>string</td><td>Document title</td><td>Dify Introduction</td></tr><tr><td>metadata</td><td>FALSE</td><td>json</td><td>Contains metadata attributes and their values for the document in the data source.</td><td>See example</td></tr></table></body></html>  

## Response Syntax  


HTTP/1.1 200
Content-type: application/json
{
    "records": [{
                    "metadata": {
                            "path": "s3://dify/knowledge.txt",
                            "description": "dify knowledge document"
                    },
                    "score": 0.98,
                    "title": "knowledge.txt",
                    "content": "This is the document for external knowledge."
            },
            {
                    "metadata": {
                            "path": "s3://dify/introduce.txt",
                            "description": "dify introduce"
                    },
                    "score": 0.66,
                    "title": "introduce.txt",
                    "content": "The Innovation Engine for GenAI Applications"
            }
    ]
}


## Errors  

If the action fails, the service sends back the following error information in JSON format:  

The error_code property has the following types:   


<html><body><table><tr><td>Property</td><td>Required</td><td>Type</td><td>Description</td><td>Examplevalue</td></tr><tr><td>error_code</td><td>TRUE</td><td>int</td><td>Error code</td><td>1001</td></tr><tr><td>error_msg</td><td>TRUE</td><td>string</td><td>The description of API exception</td><td>Invalid Authorization header format. Expected'Bearer format.</td></tr></table></body></html>  

<html><body><table><tr><td>Code Description</td></tr><tr><td>1001</td><td>InvalidAuthorizationheaderformat.</td></tr><tr><td>1002</td><td>Authorizationfailed</td></tr><tr><td>2001</td><td>The knowledge doesnot exist</td></tr></table></body></html>  

### HTTP Status Codes  

AccessDeniedException The request is denied because of missing access permissions. Check your permissions and retry your request. HTTP Status Code: 403  

InternalServerException An internal server error occurred. Retry your request. HTTP Status Code: 500  
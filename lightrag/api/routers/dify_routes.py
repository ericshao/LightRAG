"""
Dify External Knowledge API router implementation
"""

from fastapi import APIRouter, Header, HTTPException, Depends
from lightrag import LightRAG
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import os
import re
import logging
from starlette.responses import JSONResponse
from lightrag.base import QueryParam


logger = logging.getLogger(__name__)

class RetrievalSetting(BaseModel):
    top_k: int = Field(..., description="Maximum number of retrieved results")
    score_threshold: float = Field(..., description="The score threshold for relevance")

class RetrievalRequest(BaseModel):
    knowledge_id: str = Field(..., description="Your knowledge's unique ID")
    query: str = Field(..., description="User's query")
    retrieval_setting: RetrievalSetting

class DifyRecord(BaseModel):
    content: str = Field(..., description="Contains a chunk of text from a data source")
    score: float = Field(..., description="The score of relevance, range 0~1")
    title: str = Field(..., description="Document title")
    metadata: Dict = Field(default={}, description="Document metadata")

class DifyResponse(BaseModel):
    records: List[DifyRecord]


"""
用于格式化知识图谱数据的工具函数
"""

import json
import re
import io
import csv
import logging

logger = logging.getLogger(__name__)

def format_kg_to_json(kg_context: str) -> str:
    """
    将知识图谱上下文(kg_context)从CSV格式转换为JSON格式
    
    Args:
        kg_context: 包含Entities、Relationships和Sources的CSV格式字符串
    
    Returns:
        格式化的JSON字符串
    """
    # 结果字典
    result = {
        "entities": [],
        "relationships": [],
        "sources": []
    }

    # 将kg_context中所有的\"<SEP>\"替换为<SEP>
    kg_context = kg_context.replace('\"<SEP>\"', '<SEP>')

    
    # 使用正则表达式识别不同的部分
    entity_match = re.search(r'-----Entities-----\s*```csv\s*(.*?)```', kg_context, re.DOTALL)
    relation_match = re.search(r'-----Relationships-----\s*```csv\s*(.*?)```', kg_context, re.DOTALL)
    # source_match = re.search(r'-----Sources-----\s*```csv\s*(.*?)```', kg_context, re.DOTALL)
    
    # 解析实体
    if entity_match:
        entity_csv = entity_match.group(1)
        reader = csv.reader(io.StringIO(entity_csv), delimiter=',')
        headers = next(reader)
        headers = [h.strip() for h in headers]

        logging.info(f"Entity Headers: {headers}")
        
        for row in reader:
            logging.info(f"Entity Row: {row}")
            # 如果row去除空格后为空，则跳过
            if not row or all(not cell.strip() for cell in row):
                continue
            entity_dict = {}
            for i, value in enumerate(row):
                if i < len(headers):
                    # 移除头尾的引号
                    value = value.strip()
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    
                    # 处理<SEP>分隔的字段
                    if "<SEP>" in value:
                        value = [part.strip() for part in value.split("<SEP>")]
                    logging.info(f"Entity Header:{i} {headers[i]}, Value: {value}")
                    entity_dict[headers[i]] = value
            result["entities"].append(entity_dict)
    
    # 解析关系
    if relation_match:
        relation_csv = relation_match.group(1)
        reader = csv.reader(io.StringIO(relation_csv), delimiter=',', lineterminator = '\n', quotechar = '\"')
        headers = next(reader)
        headers = [h.strip() for h in headers]

        logging.info(f"Relation Headers: {headers}")
        
        for row in reader:
                        # 如果row去除空格后为空，则跳过
            if not row or all(not cell.strip() for cell in row):
                continue
            relation_dict = {}
            for i, value in enumerate(row):
                if i < len(headers):
                    # 移除头尾的引号
                    value = value.strip()
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    
                    # 处理<SEP>分隔的字段
                    if "<SEP>" in value:
                        value = [part.strip() for part in value.split("<SEP>")]
                    
                    relation_dict[headers[i]] = value
            result["relationships"].append(relation_dict)
    
    # 解析来源
    # if source_match:
    #     source_csv = source_match.group(1)
    #     reader = csv.reader(io.StringIO(source_csv), delimiter=',')
    #     headers = next(reader)
    #     headers = [h.strip() for h in headers]
        
    #     for row in reader:
    #                     # 如果row去除空格后为空，则跳过
    #         if not row or all(not cell.strip() for cell in row):
    #             continue
    #         source_dict = {}
    #         for i, value in enumerate(row):
    #             if i < len(headers):
    #                 # 移除头尾的引号
    #                 value = value.strip()
    #                 if value.startswith('"') and value.endswith('"'):
    #                     value = value[1:-1]
                    
    #                 # 处理<SEP>分隔的字段
    #                 if "<SEP>" in value:
    #                     value = [part.strip() for part in value.split("<SEP>")]
                    
    #                 source_dict[headers[i]] = value
    #         result["sources"].append(source_dict)
    
    logger.info(f"KG_JSON:\n {result}")
    # 转换为JSON字符串
    return json.dumps(result, ensure_ascii=False, indent=2)

def create_dify_routes(rag: LightRAG, api_key: Optional[str] = None) -> APIRouter:
    router = APIRouter(prefix="/dify", tags=["dify"])

    def verify_dify_auth(authorization: str = Header(..., description="Authorization header", alias="Authorization")) -> str:
        # 验证授权头格式
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=403,
                detail={
                    "error_code": 1001,
                    "error_msg": "Invalid Authorization header format. Expected 'Bearer' format."
                }
            )
        
        token = authorization.replace("Bearer ", "")
        allowed_keys = os.getenv("DIFY_API_KEYS", "").split(",")
        
        # 验证token
        if token not in allowed_keys:
            raise HTTPException(
                status_code=403,
                detail={
                    "error_code": 1002,
                    "error_msg": "Authorization failed"
                }
            )
            
        return token

    @router.post(
        "/retrieval",
        response_model=DifyResponse,
        dependencies=[Depends(verify_dify_auth)] if os.getenv("DIFY_API_KEYS") else [],
        description="Retrieve relevant content from knowledge base"
    )
    async def retrieval(request: RetrievalRequest):
        try:
            # 设置临时的cosine_better_than_threshold
            original_threshold = rag.vector_db_storage_cls_kwargs.get("cosine_better_than_threshold")
            rag.vector_db_storage_cls_kwargs["cosine_better_than_threshold"] = request.retrieval_setting.score_threshold

            try:
                # 保存原始的namespace前缀
                original_prefix = rag.namespace_prefix 
                rag.namespace_prefix = request.knowledge_id

                try:
                    # 创建查询参数
                    query_param = QueryParam(
                        mode="mix",  # 使用mix模式同时利用向量检索和知识图谱
                        top_k=request.retrieval_setting.top_k,
                        only_need_context=True,  # 只返回检索结果
                    )

                    # 执行查询
                    result = await rag.aquery(
                        query=request.query,
                        param=query_param,
                    )
                    logger.info(f"Query result: {result}")

                    # 检查知识库是否存在
                    if isinstance(result, str) and "fail" in result.lower():
                        return JSONResponse(
                            status_code=404,
                            content={
                                "error_code": 2001,
                                "error_msg": "The knowledge does not exist"
                            }
                        )

                    # 确保结果是dict格式
                    if not isinstance(result, dict):
                        logger.warning(f"Unexpected result type: {type(result)}")
                        return DifyResponse(records=[])

                    records = []

                    # 处理knowledge graph结果
                    if kg_context := result.get("kg_context"):
                        logger.debug(f"Found kg_context")
                        # 尝试将KG上下文转换为JSON格式
                        try:
                            formatted_kg_json = format_kg_to_json(kg_context)
                            records.append(DifyRecord(
                                content=formatted_kg_json,
                                score=0.99,  # 知识图谱结果给最高分
                                title="Knowledge Graph Result",
                                metadata={
                                    "source": "kg_search",
                                    "type": "kg_json_context"
                                }
                            ))
                            logger.debug("Successfully formatted KG context to JSON")
                        except Exception as e:
                            logger.error(f"Error formatting KG context to JSON: {str(e)}")
                            # 如果转换失败，退回到使用原始格式
                            records.append(DifyRecord(
                                content=kg_context,
                                score=0.99,  # 知识图谱结果给最高分
                                title="Knowledge Graph Result",
                                metadata={
                                    "source": "kg_search",
                                    "type": "kg_context"
                                }
                            ))

                    # 处理vector搜索结果
                    if vector_context := result.get("vector_context"):
                        logger.debug("Processing vector_context")
                        chunks = vector_context.split("\n--New Chunk--\n")
                        logger.debug(f"Found {len(chunks)} chunks")
                        
                        for i, chunk_content in enumerate(chunks):
                            # 移除可能的时间戳信息
                            content = chunk_content
                            created_at = None
                            if "[Created at:" in content:
                                timestamp_match = re.match(r'\[Created at: (.*?)\](.*)', content, re.DOTALL)
                                if timestamp_match:
                                    created_at = timestamp_match.group(1)
                                    content = timestamp_match.group(2)

                            content = content.strip()
                            if not content:
                                logger.debug(f"Skipping empty chunk {i}")
                                continue

                            records.append(DifyRecord(
                                content=content,
                                score=max(0.0, min(1.0, 0.8 - (i * 0.05))),
                                title=f"Vector Search Result {i+1}",
                                metadata={
                                    "source": "vector_search",
                                    "type": "chunk",
                                    "created_at": created_at
                                }
                            ))

                    # 按score排序
                    records.sort(key=lambda x: x.score, reverse=True)
                    logger.info(f"Total records before top_k limit: {len(records)}")
                    
                    # 限制返回数量
                    if len(records) > request.retrieval_setting.top_k:
                        records = records[:request.retrieval_setting.top_k]
                        logger.info(f"Limited to top {request.retrieval_setting.top_k} records")

                    return DifyResponse(records=records)

                finally:
                    # 恢复原始的namespace_prefix
                    rag.namespace_prefix = original_prefix

            finally:
                # 恢复原始的threshold
                if original_threshold is not None:
                    rag.vector_db_storage_cls_kwargs["cosine_better_than_threshold"] = original_threshold

        except Exception as e:
            logger.exception("Error in retrieval endpoint")
            # 处理通用错误
            return JSONResponse(
                status_code=500,
                content={
                    "error_code": 500,
                    "error_msg": str(e)
                }
            )

    return router
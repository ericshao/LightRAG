"""
Knowledge Graph API router implementation
"""

from fastapi import APIRouter, Body, HTTPException, Request
from typing import Any, Dict, Optional, List
import logging

from lightrag import LightRAG  # 修改导入方式

logger = logging.getLogger(__name__)

def create_kg_routes(rag: LightRAG, api_key: Optional[str] = None) -> APIRouter:
    router = APIRouter(prefix="/kg", tags=["Knowledge Graph"])

    @router.post("/insert")
    async def insert_custom_kg(
        kg_data: Dict[str, Any] = Body(...),
    ):
        """
        插入自定义知识图谱数据。

        此端点允许您将自定义知识图谱数据插入到LightRAG中。

        知识图谱数据应该采用以下格式:
        ```
        {
            "chunks": [
                {
                    "content": "文本内容",
                    "source_id": "源文档ID",
                    "chunk_order_index": 0  # 可选
                }
            ],
            "entities": [
                {
                    "entity_name": "实体名称",
                    "entity_type": "实体类型",  # 可选，默认为"UNKNOWN"
                    "description": "实体描述",  # 可选，默认为"No description provided"
                    "source_id": "源文档ID"
                }
            ],
            "relationships": [
                {
                    "src_id": "8524.11",
                    "tgt_id": "8524.1100",
                    "description": "关系描述",
                    "keywords": "关系关键词",
                    "weight": 1.0,  # 可选，默认为1.0
                    "source_id": "源文档ID"
                }
            ]
        }
        ```
        """
        try:
            # 验证知识图谱数据的结构
            required_keys = ["chunks", "entities", "relationships"]
            for key in required_keys:
                if key not in kg_data:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"知识图谱数据中缺少必需的键: {key}"
                    )

            # 调用insert_custom_kg方法
            await rag.ainsert_custom_kg(kg_data)

            return {"status": "success", "message": "知识图谱数据插入成功"}

        except Exception as e:
            logger.error(f"插入自定义知识图谱数据时出错: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/relations")
    async def insert_custom_relations(
        relations_data: List[Dict[str, Any]] = Body(...),
    ):
        """
        在已存在的实体之间添加自定义关系。
        
        此端点允许您在LightRAG中已存在的实体之间添加自定义关系。
        
        关系数据应该采用以下格式:
        ```
        [
            {
                "src_id": "源实体名称",
                "tgt_id": "目标实体名称",
                "description": "关系描述",
                "keywords": "关系关键词",
                "weight": 1.0,  # 可选，默认为1.0
                "source_id": "来源ID"  # 可选，默认为"CUSTOM_RELATION"
            }
        ]
        ```
        """
        try:
            # 验证关系数据的结构
            required_fields = ["src_id", "tgt_id", "description", "keywords"]
            for relation in relations_data:
                missing_fields = [field for field in required_fields if field not in relation]
                if missing_fields:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"关系数据中缺少必需的字段: {', '.join(missing_fields)}"
                    )
            
            # 调用insert_custom_relations方法
            result = await rag.ainsert_custom_relations(relations_data)
            
            return {
                "status": "success", 
                "message": f"已成功添加 {result['total_added']} 个关系，跳过 {result['total_skipped']} 个关系",
                "details": result
            }
            
        except Exception as e:
            logger.error(f"添加自定义关系时出错: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/entity/{entity_name}")
    async def get_entity_info(
        entity_name: str,
        include_vector_data: bool = False,
    ):
        """
        获取实体的详细信息。

        Args:
            entity_name: 实体名称（支持中文）
            include_vector_data: 是否包含向量数据库信息
        """
        try:
            # 确保entity_name能正确处理中文
            from urllib.parse import unquote
            decoded_entity_name = unquote(entity_name)
            logger.info(f"Processing entity request for: {decoded_entity_name}")
            
            entity_info = await rag.get_entity_info(decoded_entity_name, include_vector_data)
            return entity_info
            
        except Exception as e:
            logger.error(f"获取实体信息时出错: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/{node_label}")
    async def get_knowledge_graph(
        node_label: str,
        max_depth: int = 2,
    ):
        """
        获取以特定节点为中心的知识图谱。
        
        Args:
            node_label: 中心节点标签
            max_depth: 图谱深度限制
        """
        try:
            kg = await rag.get_knowledge_graph(node_label, max_depth)
            return kg
            
        except Exception as e:
            logger.error(f"获取知识图谱时出错: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("/entity/{entity_name}")
    async def delete_entity(
        entity_name: str,
    ):
        """
        删除实体及其关联关系。
        
        Args:
            entity_name: 要删除的实体名称
        """
        try:
            await rag.adelete_by_entity(entity_name)
            return {"status": "success", "message": f"实体 {entity_name} 已成功删除"}
            
        except Exception as e:
            logger.error(f"删除实体时出错: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.put("/entity/{entity_name}")
    async def update_entity(
        entity_name: str,
        entity_data: Dict[str, Any] = Body(...),
    ):
        """
        更新已存在的实体信息。
        
        此端点允许您更新LightRAG中已存在的实体的属性。
        
        实体数据应该采用以下格式:
        ```
        {
            "description": "更新后的实体描述",
            "entity_type": "更新后的实体类型",
            "其他属性": "其他值"
        }
        ```
        """
        try:
            # 确保entity_name能正确处理中文
            from urllib.parse import unquote
            decoded_entity_name = unquote(entity_name)
            
            logger.info(f"Processing update entity request for: {decoded_entity_name}")
            result = await rag.aupdate_entity(decoded_entity_name, entity_data)
            
            if result["status"] == "failed":
                raise HTTPException(status_code=400, detail=result["message"])
                
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"更新实体信息时出错: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.put("/relation/{src_entity}/{tgt_entity}")
    async def update_relation(
        src_entity: str,
        tgt_entity: str,
        relation_data: Dict[str, Any] = Body(...),
    ):
        """
        更新已存在的关系信息。
        
        此端点允许您更新LightRAG中已存在的关系的属性。
        
        关系数据应该采用以下格式:
        ```
        {
            "description": "更新后的关系描述",
            "keywords": "更新后的关系关键词",
            "weight": 2.0,
            "其他属性": "其他值"
        }
        ```
        """
        try:
            # 确保实体名称能正确处理中文
            from urllib.parse import unquote
            decoded_src_entity = unquote(src_entity)
            decoded_tgt_entity = unquote(tgt_entity)
            
            # 处理数据类型，确保数据类型正确
            processed_data = relation_data.copy()
            
            # 处理weight字段，确保是数值类型
            if "weight" in processed_data:
                try:
                    processed_data["weight"] = float(processed_data["weight"])
                except (TypeError, ValueError):
                    raise HTTPException(
                        status_code=400, 
                        detail="weight 字段必须是有效的数值"
                    )
            
            # 处理字符串字段，清理可能存在的多余引号
            string_fields = ["description", "keywords", "source_id"]
            for field in string_fields:
                if field in processed_data and isinstance(processed_data[field], str):
                    # 移除首尾多余的引号
                    if (processed_data[field].startswith('"') and processed_data[field].endswith('"')) or \
                       (processed_data[field].startswith("'") and processed_data[field].endswith("'")):
                        processed_data[field] = processed_data[field][1:-1]
            
            logger.info(f"Processing update relation request for: {decoded_src_entity} -> {decoded_tgt_entity}")
            logger.info(f"Cleaned data: {processed_data}")
            result = await rag.aupdate_relation(decoded_src_entity, decoded_tgt_entity, processed_data)
            
            if result["status"] == "failed":
                raise HTTPException(status_code=404, detail=result["message"])
                
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"更新关系信息时出错: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
            
    return router

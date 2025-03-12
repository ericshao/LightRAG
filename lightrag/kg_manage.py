"""
Knowledge Graph Management Module for LightRAG

This module provides functions for managing entities and relationships in the knowledge graph.
"""

import asyncio
from typing import Any, Dict, List, cast

from .base import StorageNameSpace
from .utils import compute_mdhash_id, logger


async def insert_custom_relations(rag, relations_data: list[dict[str, Any]]) -> dict[str, Any]:
    """
    为已存在的实体之间添加自定义关系（异步版本）
    
    Args:
        rag: LightRAG实例
        relations_data: 关系数据列表，每个关系包含以下字段:
            - src_id: 源实体名称
            - tgt_id: 目标实体名称
            - description: 关系描述
            - keywords: 关系关键词
            - weight: 可选，关系权重，默认为1.0
            - source_id: 可选，来源ID
            
    Returns:
        包含添加结果的字典:
            - added: 成功添加的关系列表
            - skipped: 跳过的关系列表
            - total_added: 成功添加的关系数量
            - total_skipped: 跳过的关系数量
    """
    update_storage = False
    added_relations = []
    skipped_relations = []
    
    try:
        # 处理并添加关系到知识图谱
        all_relationships_data: list[dict[str, str]] = []
        
        for relationship_data in relations_data:
            src_id = f'"{relationship_data["src_id"].upper()}"'
            tgt_id = f'"{relationship_data["tgt_id"].upper()}"'
            description = relationship_data["description"]
            keywords = relationship_data["keywords"]
            weight = relationship_data.get("weight", 1.0)
            source_id = relationship_data.get("source_id", "CUSTOM_RELATION")
            
            # 检查源实体和目标实体是否都存在
            src_exists = await rag.chunk_entity_relation_graph.has_node(src_id)
            tgt_exists = await rag.chunk_entity_relation_graph.has_node(tgt_id)
            
            if not src_exists or not tgt_exists:
                skipped_relations.append({
                    "src_id": src_id,
                    "tgt_id": tgt_id,
                    "reason": f"{'源' if not src_exists else '目标'}实体不存在"
                })
                continue
                
            # 将关系（边）添加到知识图谱
            await rag.chunk_entity_relation_graph.upsert_edge(
                src_id,
                tgt_id,
                edge_data={
                    "weight": weight,
                    "description": description,
                    "keywords": keywords,
                    "source_id": source_id,
                },
            )
            
            edge_data: dict[str, str] = {
                "src_id": src_id,
                "tgt_id": tgt_id,
                "description": description,
                "keywords": keywords,
            }
            all_relationships_data.append(edge_data)
            added_relations.append({
                "src_id": src_id,
                "tgt_id": tgt_id,
            })
            update_storage = True
        
        # 将关系添加到向量数据库
        if all_relationships_data:
            data_for_vdb = {
                compute_mdhash_id(dp["src_id"] + dp["tgt_id"], prefix="rel-"): {
                    "src_id": dp["src_id"],
                    "tgt_id": dp["tgt_id"],
                    "content": dp["keywords"] + dp["src_id"] + dp["tgt_id"] + dp["description"],
                }
                for dp in all_relationships_data
            }
            await rag.relationships_vdb.upsert(data_for_vdb)
            
        result = {
            "added": added_relations,
            "skipped": skipped_relations,
            "total_added": len(added_relations),
            "total_skipped": len(skipped_relations)
        }
        
        # 完成后更新存储
        if update_storage:
            await _insert_done(rag)
            
        return result
    
    except Exception as e:
        if update_storage:
            await _insert_done(rag)
        raise e


async def update_entity(rag, entity_name: str, entity_data: dict[str, Any]) -> dict[str, Any]:
    """
    更新已存在的实体信息（异步版本）
    
    Args:
        rag: LightRAG实例
        entity_name: 实体名称
        entity_data: 要更新的实体数据，可包含以下字段:
            - description: 实体描述
            - entity_type: 实体类型
            - 其他节点属性
            
    Returns:
        包含更新结果的字典:
            - status: 更新状态 ("success" 或 "failed")
            - message: 状态说明
            - updated_data: 更新后的实体数据
    """
    update_storage = False
    try:
        # formatted_entity_name = f'"{entity_name.upper()}"'
        
        # 检查实体是否存在
        entity_exists = await rag.chunk_entity_relation_graph.has_node(entity_name)
        if not entity_exists:
            return {
                "status": "failed",
                "message": f"实体 '{entity_name}' 不存在",
                "updated_data": None
            }
        
        # 获取现有节点数据
        current_node_data = await rag.chunk_entity_relation_graph.get_node(entity_name)
        if not current_node_data:
            current_node_data = {}
            
        # 合并新数据，保留源ID等关键信息
        updated_node_data = {**current_node_data, **entity_data}
        
        # 保持source_id不变
        # if "source_id" in current_node_data and "source_id" not in entity_data:
        #     updated_node_data["source_id"] = current_node_data["source_id"]
        
        # 更新图数据库中的节点
        await rag.chunk_entity_relation_graph.upsert_node(entity_name, updated_node_data)
        
        # 更新向量数据库中的实体表示
        entity_id = compute_mdhash_id(entity_name, prefix="ent-")
        entity_content = f"{entity_name}{updated_node_data.get('description', '')}"
        
        await rag.entities_vdb.upsert({
            entity_id: {
                "content": entity_content,
                "entity_name": entity_name
            }
        })
        
        update_storage = True
        
        result = {
            "status": "success",
            "message": f"实体 '{entity_name}' 已成功更新",
            "updated_data": updated_node_data
        }
        
        # 完成后更新存储
        if update_storage:
            await _insert_done(rag)
            
        return result
        
    except Exception as e:
        if update_storage:
            await _insert_done(rag)
        raise e


async def update_relation(rag, src_entity: str, tgt_entity: str, relation_data: dict[str, Any]) -> dict[str, Any]:
    """
    更新已存在的关系信息（异步版本）
    
    Args:
        rag: LightRAG实例
        src_entity: 源实体名称
        tgt_entity: 目标实体名称
        relation_data: 要更新的关系数据，可包含以下字段:
            - description: 关系描述
            - keywords: 关系关键词
            - weight: 关系权重
            - 其他边属性
            
    Returns:
        包含更新结果的字典:
            - status: 更新状态 ("success" 或 "failed")
            - message: 状态说明
            - updated_data: 更新后的关系数据
    """
    update_storage = False
    try:
        formatted_src_entity = f'"{src_entity.upper()}"'
        formatted_tgt_entity = f'"{tgt_entity.upper()}"'
        
        # 检查两个实体是否都存在
        src_exists = await rag.chunk_entity_relation_graph.has_node(formatted_src_entity)
        tgt_exists = await rag.chunk_entity_relation_graph.has_node(formatted_tgt_entity)
        
        if not src_exists:
            return {
                "status": "failed",
                "message": f"源实体 '{src_entity}' 不存在",
                "updated_data": None
            }
            
        if not tgt_exists:
            return {
                "status": "failed", 
                "message": f"目标实体 '{tgt_entity}' 不存在",
                "updated_data": None
            }
        
        # 检查关系是否存在
        edge_exists = await rag.chunk_entity_relation_graph.has_edge(formatted_src_entity, formatted_tgt_entity)
        if not edge_exists:
            return {
                "status": "failed",
                "message": f"从 '{src_entity}' 到 '{tgt_entity}' 的关系不存在",
                "updated_data": None
            }
        
        # 获取现有边数据
        current_edge_data = await rag.chunk_entity_relation_graph.get_edge(formatted_src_entity, formatted_tgt_entity)
        if not current_edge_data:
            current_edge_data = {}
        
        # 合并新数据，保留源ID等关键信息
        updated_edge_data = {**current_edge_data, **relation_data}
        
        # 保持source_id不变
        if "source_id" in current_edge_data and "source_id" not in relation_data:
            updated_edge_data["source_id"] = current_edge_data["source_id"]
        
        # 更新图数据库中的边
        await rag.chunk_entity_relation_graph.upsert_edge(formatted_src_entity, formatted_tgt_entity, updated_edge_data)
        
        # 更新向量数据库中的关系表示
        rel_id = compute_mdhash_id(formatted_src_entity + formatted_tgt_entity, prefix="rel-")
        keywords = updated_edge_data.get("keywords", "")
        description = updated_edge_data.get("description", "")
        
        await rag.relationships_vdb.upsert({
            rel_id: {
                "src_id": formatted_src_entity,
                "tgt_id": formatted_tgt_entity,
                "content": keywords + formatted_src_entity + formatted_tgt_entity + description,
            }
        })
        
        update_storage = True
        
        result = {
            "status": "success",
            "message": f"从 '{src_entity}' 到 '{tgt_entity}' 的关系已成功更新",
            "updated_data": updated_edge_data
        }
        
        # 完成后更新存储
        if update_storage:
            await _insert_done(rag)
            
        return result
        
    except Exception as e:
        if update_storage:
            await _insert_done(rag)
        raise e


async def _insert_done(rag) -> None:
    """更新存储索引"""
    tasks = [
        cast(StorageNameSpace, storage_inst).index_done_callback()
        for storage_inst in [
            rag.entities_vdb,
            rag.relationships_vdb,
            rag.chunk_entity_relation_graph,
        ]
        if storage_inst is not None
    ]
    await asyncio.gather(*tasks)
    logger.info("KG Management operation completed")

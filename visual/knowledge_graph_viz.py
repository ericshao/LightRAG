from pyvis.network import Network
import os
import webbrowser
from IPython.display import HTML

def visualize_knowledge_graph(graph_data, output_file="knowledge_graph.html"):
    """
    可视化知识图谱，支持中文显示和拖拽效果，实体名称更明显显示
    
    Args:
        graph_data (dict): 包含实体和关系的字典数据
        output_file (str): 输出HTML文件的路径
    """
    # 创建网络图对象
    net = Network(height="100vh", width="100%", bgcolor="#ffffff", font_color="black", notebook=False)
    
    # 增强配置网络属性，确保中文显示和拖拽效果，以及增强实体名称显示效果
    net.set_options("""
    var options = {
        "nodes": {
            "shape": "box",
            "size": 25,
            "font": {
                "size": 56,
                "face": "Arial, sans-serif",
                "bold": true,
                "color": "#000000"
            },
            "borderWidth": 3,
            "borderWidthSelected": 5,
            "labelHighlightBold": true,
            "margin": 10,
            "shadow": {
                "enabled": true,
                "color": "rgba(0,0,0,0.5)",
                "size": 5,
                "x": 2,
                "y": 2
            }
        },
        "edges": {
            "color": {
                "inherit": true
            },
            "width": 1.5,
            "smooth": {
                "enabled": true,
                "type": "dynamic"
            },
            "font": {
                "size": 32,
                "face": "Arial, sans-serif" 
            }
        },
        "physics": {
            "enabled": true,
            "stabilization": {
                "iterations": 100
            },
            "barnesHut": {
                "gravitationalConstant": -80000,
                "springConstant": 0.001,
                "springLength": 250
            }
        },
        "interaction": {
            "dragNodes": true,
            "dragView": true,
            "zoomView": true,
            "hover": true
        }
    }
    """)
    
    # 根据实体类型设置不同颜色
    color_map = {
        "CATEGORY": "#4682B4",  # 钢蓝色
        "PRODUCT": "#2E8B57",   # 海绿色
        "ORGANIZATION": "#D2691E",  # 巧克力色
        "DEFAULT": "#9370DB"    # 中紫色
    }
    
    # 跟踪已添加的节点
    added_nodes = set()
    
    # 添加实体节点，增强显示效果
    for entity in graph_data.get("entities", []):
        entity_name = entity["entity"]
        entity_type = entity.get("type", "DEFAULT")
        description = entity.get("description", "")
        
        # 处理描述可能是列表的情况
        if isinstance(description, list):
            description = " ".join(description)
            
        # 根据实体类型设置颜色
        color = color_map.get(entity_type, color_map["DEFAULT"])
        
        # 尝试获取实体的rank值，用于调整节点大小
        try:
            rank = float(entity.get("rank", 5))
            # 将rank值映射到节点大小，确保所有节点都有合适的大小
            node_size = 20 + (rank / 2)  # 这样rank为10的节点大小为25，以此类推
        except (ValueError, TypeError):
            node_size = 25  # 默认大小
        
        # 构建带HTML格式的标签，使显示更突出
        html_label = f"<div style='background-color:rgba(255,255,255,0.7); padding:5px; border-radius:5px;'>{entity_name}</div>"
        
        # 添加节点，设置提示文本和样式
        net.add_node(
            entity_name, 
            label=entity_name, 
            title=f"<div style='font-size:14px'><b>{entity_name}</b><br/><hr/>{description}</div>",
            color=color,
            size=node_size,
            borderWidth=3,
            font={'size': 16, 'color': 'black', 'face': 'Arial, sans-serif'}
        )
        added_nodes.add(entity_name)
    
    # 添加关系边
    for relation in graph_data.get("relationships", []):
        source = relation["source"]
        target = relation["target"]
        
        # 获取关系描述和权重
        rel_description = relation.get("description", "")
        
        # 添加容错处理：尝试将weight转换为浮点数，如果失败则使用默认值
        try:
            weight = float(relation.get("weight", 1))
        except (ValueError, TypeError):
            # 如果转换失败，使用默认值并打印警告
            default_weight = 1.0
            print(f"警告: 无法将权重值 '{relation.get('weight')}' 转换为浮点数，使用默认值 {default_weight}")
            weight = default_weight
        
        # 根据权重设置边的粗细
        width = weight / 2
        
        # 检查源节点是否存在，如果不存在则添加
        if source not in added_nodes:
            net.add_node(
                source, 
                label=source, 
                title=f"自动创建的节点: {source}", 
                color=color_map["DEFAULT"],
                size=20,
                font={'size': 16, 'color': 'black', 'face': 'Arial, sans-serif'}
            )
            added_nodes.add(source)
            print(f"自动创建了缺失的源节点: {source}")
        
        # 检查目标节点是否存在，如果不存在则添加
        if target not in added_nodes:
            net.add_node(
                target, 
                label=target, 
                title=f"自动创建的节点: {target}", 
                color=color_map["DEFAULT"],
                size=20,
                font={'size': 16, 'color': 'black', 'face': 'Arial, sans-serif'}
            )
            added_nodes.add(target)
            print(f"自动创建了缺失的目标节点: {target}")
        
        # 添加边，优化显示
        net.add_edge(
            source, 
            target, 
            title=f"<div style='font-size:12px'>{rel_description}</div>", 
            value=width, 
            width=width,
            color={'color': '#666666', 'opacity': 0.8}
        )
    
    # 生成并保存HTML文件
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_file)
    net.save_graph(output_path)
    print(f"知识图谱已保存至 {output_path}")
    
    # 在浏览器中打开
    webbrowser.open('file://' + os.path.abspath(output_path))
    
    # 在Jupyter环境中显示
    try:
        return HTML(filename=output_path)
    except:
        pass

if __name__ == "__main__":
    # 从knowledge_graph.py导入图谱数据
    from knowledge_graph import graphData
    
    # 可视化知识图谱
    visualize_knowledge_graph(graphData)

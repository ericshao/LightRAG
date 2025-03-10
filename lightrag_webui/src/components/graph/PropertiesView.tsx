import { useEffect, useState } from 'react'
import { useGraphStore, RawNodeType, RawEdgeType } from '@/stores/graph'
import Text from '@/components/ui/Text'
import useLightragGraph from '@/hooks/useLightragGraph'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { toast } from 'sonner'
import { Pencil, Save, X } from 'lucide-react'

/**
 * Component that view properties of elements in graph.
 */
const PropertiesView = () => {
  const { getNode, getEdge } = useLightragGraph()
  const selectedNode = useGraphStore.use.selectedNode()
  const focusedNode = useGraphStore.use.focusedNode()
  const selectedEdge = useGraphStore.use.selectedEdge()
  const focusedEdge = useGraphStore.use.focusedEdge()

  const [currentElement, setCurrentElement] = useState<NodeType | EdgeType | null>(null)
  const [currentType, setCurrentType] = useState<'node' | 'edge' | null>(null)

  useEffect(() => {
    let type: 'node' | 'edge' | null = null
    let element: RawNodeType | RawEdgeType | null = null
    if (focusedNode) {
      type = 'node'
      element = getNode(focusedNode)
    } else if (selectedNode) {
      type = 'node'
      element = getNode(selectedNode)
    } else if (focusedEdge) {
      type = 'edge'
      element = getEdge(focusedEdge, true)
    } else if (selectedEdge) {
      type = 'edge'
      element = getEdge(selectedEdge, true)
    }

    if (element) {
      if (type == 'node') {
        setCurrentElement(refineNodeProperties(element as any))
      } else {
        setCurrentElement(refineEdgeProperties(element as any))
      }
      setCurrentType(type)
    } else {
      setCurrentElement(null)
      setCurrentType(null)
    }
  }, [
    focusedNode,
    selectedNode,
    focusedEdge,
    selectedEdge,
    setCurrentElement,
    setCurrentType,
    getNode,
    getEdge
  ])

  if (!currentElement) {
    return <></>
  }
  return (
    <div className="bg-background/80 max-w-xs rounded-lg border-2 p-2 text-xs backdrop-blur-lg">
      {currentType == 'node' ? (
        <NodePropertiesView node={currentElement as any} />
      ) : (
        <EdgePropertiesView edge={currentElement as any} />
      )}
    </div>
  )
}

type NodeType = RawNodeType & {
  relationships: {
    type: string
    id: string
    label: string
  }[]
}

type EdgeType = RawEdgeType & {
  sourceNode?: RawNodeType
  targetNode?: RawNodeType
}

const refineNodeProperties = (node: RawNodeType): NodeType => {
  const state = useGraphStore.getState()
  const relationships = []

  if (state.sigmaGraph && state.rawGraph) {
    for (const edgeId of state.sigmaGraph.edges(node.id)) {
      const edge = state.rawGraph.getEdge(edgeId, true)
      if (edge) {
        const isTarget = node.id === edge.source
        const neighbourId = isTarget ? edge.target : edge.source
        const neighbour = state.rawGraph.getNode(neighbourId)
        if (neighbour) {
          relationships.push({
            type: isTarget ? 'Target' : 'Source',
            id: neighbourId,
            label: neighbour.labels.join(', ')
          })
        }
      }
    }
  }
  return {
    ...node,
    relationships
  }
}

const refineEdgeProperties = (edge: RawEdgeType): EdgeType => {
  const state = useGraphStore.getState()
  const sourceNode = state.rawGraph?.getNode(edge.source)
  const targetNode = state.rawGraph?.getNode(edge.target)
  return {
    ...edge,
    sourceNode,
    targetNode
  }
}

const PropertyRow = ({
  name,
  value,
  onClick,
  tooltip,
  editable = false,
  onChange,
  isEditing = false
}: {
  name: string
  value: any
  onClick?: () => void
  tooltip?: string
  editable?: boolean
  onChange?: (value: string) => void
  isEditing?: boolean
}) => {
  return (
    <div className="flex items-center gap-2">
      <label className="text-primary/60 tracking-wide">{name}</label>:
      {!isEditing ? (
        <Text
          className={`rounded p-1 text-ellipsis ${editable ? 'hover:bg-primary/20' : ''}`}
          tooltipClassName="max-w-80"
          text={value}
          tooltip={tooltip || value}
          side="left"
          onClick={onClick}
        />
      ) : (
        <Input
          className="h-6 w-full text-xs py-1 px-2"
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
        />
      )}
    </div>
  )
}

async function updateEntityApi(entityName: string, entityData: any) {
  try {
    // 去掉实体名称中的引号，API会自动添加
    const cleanEntityName = entityName.replace(/"/g, '')

    const response = await fetch(`/kg/entity/${encodeURIComponent(cleanEntityName)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(entityData)
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || '更新实体信息失败')
    }

    return await response.json()
  } catch (error) {
    console.error('更新实体信息时出错:', error)
    throw error
  }
}

// 修改更新关系属性的 API 函数
async function updateRelationshipApi(sourceId: string, targetId: string, relationshipData: any) {
  try {
    const response = await fetch(`/kg/relation/${encodeURIComponent(sourceId)}/${encodeURIComponent(targetId)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(relationshipData)
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || '更新关系信息失败')
    }

    return await response.json()
  } catch (error) {
    console.error('更新关系信息时出错:', error)
    throw error
  }
}

const NodePropertiesView = ({ node }: { node: NodeType }) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editableProperties, setEditableProperties] = useState<Record<string, string>>({})

  // 当节点改变时，重置编辑状态
  useEffect(() => {
    setIsEditing(false)
    setEditableProperties({})
  }, [node.id])

  // 开始编辑时，初始化可编辑属性
  const handleEdit = () => {
    setEditableProperties(
      Object.fromEntries(
        Object.entries(node.properties)
          .filter(([key]) => key !== 'source_id') // 排除source_id不允许编辑
          .map(([key, value]) => [key, String(value)])
      )
    )
    setIsEditing(true)
  }

  // 取消编辑
  const handleCancel = () => {
    setIsEditing(false)
    setEditableProperties({})
  }

  // 保存编辑
  const handleSave = async () => {
    try {
      const result = await updateEntityApi(node.labels.join(''), editableProperties)

      if (result.status === 'success') {
        toast.success('更新成功', {
          description: result.message
        })
        setIsEditing(false)

        // 重新加载图表或更新本地状态
        setTimeout(() => {
          window.location.reload()
        }, 1000)
      } else {
        toast.error('更新失败', {
          description: result.message
        })
      }
    } catch (error) {
      toast.error('更新失败', {
        description: error instanceof Error ? error.message : '未知错误'
      })
    }
  }

  // 更新属性值
  const handlePropertyChange = (key: string, value: string) => {
    setEditableProperties(prev => ({
      ...prev,
      [key]: value
    }))
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <label className="text-md pl-1 font-bold tracking-wide text-sky-300">Node</label>
        {!isEditing ? (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={handleEdit}
            title="编辑属性"
          >
            <Pencil className="h-4 w-4" />
          </Button>
        ) : (
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 text-red-500"
              onClick={handleCancel}
              title="取消编辑"
            >
              <X className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 text-green-500"
              onClick={handleSave}
              title="保存更改"
            >
              <Save className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
      <div className="bg-primary/5 max-h-96 overflow-auto rounded p-1">
        <PropertyRow name={'Id'} value={node.id} />
        <PropertyRow
          name={'Labels'}
          value={node.labels.join(', ')}
          onClick={() => {
            useGraphStore.getState().setSelectedNode(node.id, true)
          }}
        />
        <PropertyRow name={'Degree'} value={node.degree} />
      </div>
      <label className="text-md pl-1 font-bold tracking-wide text-yellow-400/90">Properties</label>
      <div className="bg-primary/5 max-h-96 overflow-auto rounded p-1">
        {Object.keys(node.properties)
          .sort()
          .map((name) => {
            // source_id不允许编辑
            const canEdit = name !== 'source_id'

            return (
              <PropertyRow
                key={name}
                name={name}
                value={isEditing && canEdit ? editableProperties[name] : node.properties[name]}
                editable={canEdit}
                isEditing={isEditing && canEdit}
                onChange={(value) => handlePropertyChange(name, value)}
              />
            )
          })}
      </div>
      {node.relationships.length > 0 && (
        <>
          <label className="text-md pl-1 font-bold tracking-wide text-teal-600/90">
            Relationships
          </label>
          <div className="bg-primary/5 max-h-96 overflow-auto rounded p-1">
            {node.relationships.map(({ type, id, label }) => {
              return (
                <PropertyRow
                  key={id}
                  name={type}
                  value={label}
                  onClick={() => {
                    useGraphStore.getState().setSelectedNode(id, true)
                  }}
                />
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

const EdgePropertiesView = ({ edge }: { edge: EdgeType }) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editableProperties, setEditableProperties] = useState<Record<string, string>>({})

  // 当边改变时，重置编辑状态
  useEffect(() => {
    setIsEditing(false)
    setEditableProperties({})
  }, [edge.id])

  // 开始编辑时，初始化可编辑属性
  const handleEdit = () => {
    setEditableProperties(
      Object.fromEntries(
        Object.entries(edge.properties)
          .map(([key, value]) => [key, String(value)])
      )
    )
    setIsEditing(true)
  }

  // 取消编辑
  const handleCancel = () => {
    setIsEditing(false)
    setEditableProperties({})
  }

  // 保存编辑
  const handleSave = async () => {
    if (!edge.sourceNode) {
      toast.error('无法更新关系', {
        description: '源节点不存在'
      })
      return
    }
    if (!edge.targetNode) {
      toast.error('无法更新关系', {
        description: '目标节点不存在'
      })
      return
    }
    try {
      const result = await updateRelationshipApi(edge.sourceNode.labels.join(''), edge.targetNode.labels.join(''), editableProperties)

      if (result.status === 'success') {
        toast.success('更新关系成功', {
          description: result.message
        })
        setIsEditing(false)

        // 重新加载图表或更新本地状态
        setTimeout(() => {
          window.location.reload()
        }, 1000)
      } else {
        toast.error('更新关系失败', {
          description: result.message
        })
      }
    } catch (error) {
      toast.error('更新关系失败', {
        description: error instanceof Error ? error.message : '未知错误'
      })
    }
  }

  // 更新属性值
  const handlePropertyChange = (key: string, value: string) => {
    setEditableProperties(prev => ({
      ...prev,
      [key]: value
    }))
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <label className="text-md pl-1 font-bold tracking-wide text-teal-600">Relationship</label>
        {!isEditing ? (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={handleEdit}
            title="编辑关系属性"
          >
            <Pencil className="h-4 w-4" />
          </Button>
        ) : (
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 text-red-500"
              onClick={handleCancel}
              title="取消编辑"
            >
              <X className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 text-green-500"
              onClick={handleSave}
              title="保存更改"
            >
              <Save className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
      <div className="bg-primary/5 max-h-96 overflow-auto rounded p-1">
        <PropertyRow name={'Id'} value={edge.id} />
        {edge.type && <PropertyRow name={'Type'} value={edge.type} />}
        <PropertyRow
          name={'Source'}
          value={edge.sourceNode ? edge.sourceNode.labels.join(', ') : edge.source}
          onClick={() => {
            useGraphStore.getState().setSelectedNode(edge.source, true)
          }}
        />
        <PropertyRow
          name={'Target'}
          value={edge.targetNode ? edge.targetNode.labels.join(', ') : edge.target}
          onClick={() => {
            useGraphStore.getState().setSelectedNode(edge.target, true)
          }}
        />
      </div>
      <label className="text-md pl-1 font-bold tracking-wide text-yellow-400/90">Properties</label>
      <div className="bg-primary/5 max-h-96 overflow-auto rounded p-1">
        {Object.keys(edge.properties)
          .sort()
          .map((name) => (
            <PropertyRow
              key={name}
              name={name}
              value={isEditing ? editableProperties[name] : edge.properties[name]}
              editable={true}
              isEditing={isEditing}
              onChange={(value) => handlePropertyChange(name, value)}
            />
          ))}
      </div>
    </div>
  )
}

export default PropertiesView

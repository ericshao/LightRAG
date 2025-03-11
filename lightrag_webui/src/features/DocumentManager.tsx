import { useState, useEffect, useCallback, useMemo } from 'react'
import Button from '@/components/ui/Button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/Table'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import EmptyCard from '@/components/ui/EmptyCard'
import Text from '@/components/ui/Text'
import UploadDocumentsDialog from '@/components/documents/UploadDocumentsDialog'
import ClearDocumentsDialog from '@/components/documents/ClearDocumentsDialog'

import { getDocuments, scanNewDocuments, DocsStatusesResponse, DocStatus } from '@/api/lightrag'
import { errorMessage } from '@/lib/utils'
import { toast } from 'sonner'
import { useBackendState } from '@/stores/state'

import { RefreshCwIcon, ChevronUpIcon, ChevronDownIcon, FilterIcon } from 'lucide-react'

// 定义排序方向类型
type SortDirection = 'asc' | 'desc' | null;
// 定义可排序列类型
type SortableColumn = 'updated_at' | 'created_at' | 'content_length' | 'chunks_count';
// 定义文档状态类型
type StatusFilter = DocStatus | 'all';

export default function DocumentManager() {
  const health = useBackendState.use.health()
  const [docs, setDocs] = useState<DocsStatusesResponse | null>(null)
  // 添加排序状态
  const [sortColumn, setSortColumn] = useState<SortableColumn | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);
  // 添加过滤状态
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const fetchDocuments = useCallback(async () => {
    try {
      const docs = await getDocuments()
      if (docs && docs.statuses) {
        // compose all documents count
        const numDocuments = Object.values(docs.statuses).reduce(
          (acc, status) => acc + status.length,
          0
        )
        if (numDocuments > 0) {
          setDocs(docs)
        } else {
          setDocs(null)
        }
        // console.log(docs)
      } else {
        setDocs(null)
      }
    } catch (err) {
      toast.error('Failed to load documents\n' + errorMessage(err))
    }
  }, [setDocs])

  useEffect(() => {
    fetchDocuments()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const scanDocuments = useCallback(async () => {
    try {
      const { status } = await scanNewDocuments()
      toast.message(status)
    } catch (err) {
      toast.error('Failed to load documents\n' + errorMessage(err))
    }
  }, [])

  useEffect(() => {
    const interval = setInterval(async () => {
      if (!health) {
        return
      }
      try {
        await fetchDocuments()
      } catch (err) {
        toast.error('Failed to get scan progress\n' + errorMessage(err))
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [health, fetchDocuments])

  // 过滤和排序文档
  const filteredAndSortedDocs = useMemo(() => {
    if (!docs) return null;

    // 创建一个过滤后的文档对象
    let filteredDocs = { ...docs };

    // 应用状态过滤
    if (statusFilter !== 'all') {
      filteredDocs = {
        ...docs,
        statuses: {
          pending: [],
          processing: [],
          processed: [],
          failed: [],
          [statusFilter]: docs.statuses[statusFilter] || []
        }
      };
    }

    // 如果没有排序，直接返回过滤后的文档
    if (!sortColumn || !sortDirection) return filteredDocs;

    // 应用排序
    const sortedStatuses = Object.entries(filteredDocs.statuses).reduce((acc, [status, documents]) => {
      const sortedDocuments = [...documents].sort((a, b) => {
        if (sortDirection === 'asc') {
          return (a[sortColumn] ?? 0) > (b[sortColumn] ?? 0) ? 1 : -1;
        } else {
          return (a[sortColumn] ?? 0) < (b[sortColumn] ?? 0) ? 1 : -1;
        }
      });
      acc[status as DocStatus] = sortedDocuments;
      return acc;
    }, {} as DocsStatusesResponse['statuses']);

    return { ...filteredDocs, statuses: sortedStatuses };
  }, [docs, sortColumn, sortDirection, statusFilter]);

  // 切换排序状态
  const toggleSort = (column: SortableColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  // 计算各状态文档数量
  const documentCounts = useMemo(() => {
    if (!docs) return { all: 0 } as Record<string, number>;

    const counts: Record<string, number> = { all: 0 };

    Object.entries(docs.statuses).forEach(([status, documents]) => {
      counts[status as DocStatus] = documents.length;
      counts.all += documents.length;
    });

    return counts;
  }, [docs]);

  return (
    <Card className="!size-full !rounded-none !border-none">
      <CardHeader>
        <CardTitle className="text-lg">Document Management</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={scanDocuments}
            side="bottom"
            tooltip="Scan documents"
            size="sm"
          >
            <RefreshCwIcon /> Scan
          </Button>
          <div className="flex-1" />
          <ClearDocumentsDialog />
          <UploadDocumentsDialog />
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Uploaded documents</CardTitle>
          </CardHeader>
          <CardContent>
            {!docs && (
              <EmptyCard
                title="No documents uploaded"
                description="upload documents to see them here"
              />
            )}
            {docs && (
              <>
                <div className="flex items-center gap-2 mb-4">
                  <FilterIcon className="h-4 w-4" />
                  <span>Filter:</span>
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant={statusFilter === 'all' ? 'default' : 'outline'}
                      onClick={() => setStatusFilter('all')}
                    >
                      All ({documentCounts.all})
                    </Button>
                    <Button
                      size="sm"
                      variant={statusFilter === 'processed' ? 'default' : 'outline'}
                      onClick={() => setStatusFilter('processed')}
                      className="text-green-600"
                    >
                      Completed ({documentCounts.processed || 0})
                    </Button>
                    <Button
                      size="sm"
                      variant={statusFilter === 'processing' ? 'default' : 'outline'}
                      onClick={() => setStatusFilter('processing')}
                      className="text-blue-600"
                    >
                      Processing ({documentCounts.processing || 0})
                    </Button>
                    <Button
                      size="sm"
                      variant={statusFilter === 'pending' ? 'default' : 'outline'}
                      onClick={() => setStatusFilter('pending')}
                      className="text-yellow-600"
                    >
                      Pending ({documentCounts.pending || 0})
                    </Button>
                    <Button
                      size="sm"
                      variant={statusFilter === 'failed' ? 'default' : 'outline'}
                      onClick={() => setStatusFilter('failed')}
                      className="text-red-600"
                    >
                      Failed ({documentCounts.failed || 0})
                    </Button>
                  </div>
                </div>

                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>Summary</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Length</TableHead>
                      <TableHead>Chunks</TableHead>
                      <TableHead onClick={() => toggleSort('created_at')} className="cursor-pointer hover:bg-background/60">
                        Created
                        {sortColumn === 'created_at' && (
                          sortDirection === 'asc' ? <ChevronUpIcon className="inline ml-1" /> : <ChevronDownIcon className="inline ml-1" />
                        )}
                      </TableHead>
                      <TableHead onClick={() => toggleSort('updated_at')} className="cursor-pointer hover:bg-background/60">
                        Updated
                        {sortColumn === 'updated_at' && (
                          sortDirection === 'asc' ? <ChevronUpIcon className="inline ml-1" /> : <ChevronDownIcon className="inline ml-1" />
                        )}
                      </TableHead>
                      <TableHead>Metadata</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody className="text-sm">
                    {filteredAndSortedDocs?.statuses && Object.entries(filteredAndSortedDocs.statuses).map(([status, documents]) =>
                      documents.map((doc) => (
                        <TableRow key={doc.id}>
                          <TableCell className="truncate font-mono">{doc.id}</TableCell>
                          <TableCell className="max-w-xs min-w-24 truncate">
                            <Text
                              text={doc.content_summary}
                              tooltip={doc.content_summary}
                              tooltipClassName="max-w-none overflow-visible block"
                            />
                          </TableCell>
                          <TableCell>
                            {status === 'processed' && (
                              <span className="text-green-600">Completed</span>
                            )}
                            {status === 'processing' && (
                              <span className="text-blue-600">Processing</span>
                            )}
                            {status === 'pending' && <span className="text-yellow-600">Pending</span>}
                            {status === 'failed' && <span className="text-red-600">Failed</span>}
                            {doc.error && (
                              <span className="ml-2 text-red-500" title={doc.error}>
                                ⚠️
                              </span>
                            )}
                          </TableCell>
                          <TableCell>{doc.content_length ?? '-'}</TableCell>
                          <TableCell>{doc.chunks_count ?? '-'}</TableCell>
                          <TableCell className="truncate">
                            {new Date(doc.created_at).toLocaleString()}
                          </TableCell>
                          <TableCell className="truncate">
                            {new Date(doc.updated_at).toLocaleString()}
                          </TableCell>
                          <TableCell className="max-w-xs truncate">
                            {doc.metadata ? JSON.stringify(doc.metadata) : '-'}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </>
            )}
          </CardContent>
        </Card>
      </CardContent>
    </Card>
  )
}

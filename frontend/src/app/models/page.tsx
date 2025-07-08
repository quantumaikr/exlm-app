'use client';

import { Bot, Edit, MoreVertical, Play, Plus, Search, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { toast } from 'react-hot-toast';

import { ModelListSkeleton } from '@/components/loading-skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Model, modelsService, ModelStatus } from '@/services/models';
import { AlertCircle } from 'lucide-react';

const statusColors = {
  [ModelStatus.PENDING]: 'bg-gray-500',
  [ModelStatus.TRAINING]: 'bg-blue-500',
  [ModelStatus.COMPLETED]: 'bg-green-500',
  [ModelStatus.FAILED]: 'bg-red-500',
};

const statusLabels = {
  [ModelStatus.PENDING]: '대기 중',
  [ModelStatus.TRAINING]: '학습 중',
  [ModelStatus.COMPLETED]: '완료',
  [ModelStatus.FAILED]: '실패',
};

export default function ModelsPage() {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const { sendMessage } = useWebSocket();

  const fetchModels = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await modelsService.getModels({
        page,
        search: search || undefined,
      });
      setModels(response.items);
      setTotalPages(response.pages);
    } catch (error) {
      setError('모델을 불러오는데 실패했습니다. 잠시 후 다시 시도해주세요.');
      toast.error('모델을 불러오는데 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, [page, search]);

  // WebSocket 메시지 핸들러
  useWebSocket((message) => {
    if (message.type === 'model_training_started') {
      toast.success(`모델 학습이 시작되었습니다: ${message.data?.model_name}`);
      fetchModels();
    } else if (message.type === 'model_training_completed') {
      toast.success(`모델 학습이 완료되었습니다: ${message.data?.model_name}`);
      fetchModels();
    } else if (message.type === 'model_training_failed') {
      toast.error(`모델 학습이 실패했습니다: ${message.data?.model_name}`);
      fetchModels();
    }
  });

  const handleStartTraining = async (model: Model) => {
    try {
      await modelsService.startTraining(model.id);
      toast.success('학습이 시작되었습니다');
      fetchModels();
    } catch (error) {
      toast.error('학습 시작에 실패했습니다');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('정말로 이 모델을 삭제하시겠습니까?')) return;

    try {
      await modelsService.deleteModel(id);
      toast.success('모델이 삭제되었습니다');
      fetchModels();
    } catch (error) {
      toast.error('모델 삭제에 실패했습니다');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">모델</h1>
          <p className="text-muted-foreground mt-2">
            AI 모델을 학습하고 관리합니다
          </p>
        </div>
        <Button asChild>
          <Link href="/models/new">
            <Plus className="mr-2 h-4 w-4" />
            새 모델
          </Link>
        </Button>
      </div>

      <div className="flex items-center space-x-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
          <Input
            placeholder="모델 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {loading ? (
        <ModelListSkeleton />
      ) : error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>오류</AlertTitle>
          <AlertDescription>
            {error}
            <Button 
              variant="link" 
              className="pl-2" 
              onClick={() => fetchModels()}
            >
              다시 시도
            </Button>
          </AlertDescription>
        </Alert>
      ) : models.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <Bot className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground mb-4">
              {search ? '검색 결과가 없습니다' : '아직 모델이 없습니다'}
            </p>
            {!search && (
              <Button asChild>
                <Link href="/models/new">첫 모델 만들기</Link>
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {models.map((model) => (
            <Card key={model.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <CardTitle className="line-clamp-1">
                        <Link
                          href={`/models/${model.id}`}
                          className="hover:underline"
                        >
                          {model.name}
                        </Link>
                      </CardTitle>
                      <Badge className={statusColors[model.status]}>
                        {statusLabels[model.status]}
                      </Badge>
                    </div>
                    <CardDescription className="line-clamp-2 mt-2">
                      베이스 모델: {model.base_model}
                    </CardDescription>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      {model.status === ModelStatus.PENDING && (
                        <DropdownMenuItem onClick={() => handleStartTraining(model)}>
                          <Play className="mr-2 h-4 w-4" />
                          학습 시작
                        </DropdownMenuItem>
                      )}
                      <DropdownMenuItem asChild>
                        <Link href={`/models/${model.id}/edit`}>
                          <Edit className="mr-2 h-4 w-4" />
                          편집
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => handleDelete(model.id)}
                        className="text-destructive"
                        disabled={model.status === ModelStatus.TRAINING}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        삭제
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  생성일: {formatDate(model.created_at)}
                </p>
                {model.metrics && (
                  <div className="mt-2 space-y-1">
                    <p className="text-sm font-medium">메트릭:</p>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      {Object.entries(model.metrics).slice(0, 4).map(([key, value]) => (
                        <div key={key}>
                          <span className="text-muted-foreground">{key}:</span>{' '}
                          <span>{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center space-x-2">
          <Button
            variant="outline"
            onClick={() => setPage(page - 1)}
            disabled={page === 1}
          >
            이전
          </Button>
          <span className="flex items-center px-4">
            {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            onClick={() => setPage(page + 1)}
            disabled={page === totalPages}
          >
            다음
          </Button>
        </div>
      )}
    </div>
  );
}
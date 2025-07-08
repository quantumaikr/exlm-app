'use client';

import { Edit, MoreVertical, Plus, Search, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { toast } from 'react-hot-toast';

import { ProjectsListSkeleton } from '@/components/loading-skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
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
import { Project, projectsService } from '@/services/projects';
import { AlertCircle } from 'lucide-react';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const { sendMessage } = useWebSocket();

  const fetchProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await projectsService.getProjects({
        page,
        search: search || undefined,
      });
      setProjects(response.items);
      setTotalPages(response.pages);
    } catch (error) {
      setError('프로젝트를 불러오는데 실패했습니다. 잠시 후 다시 시도해주세요.');
      toast.error('프로젝트를 불러오는데 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, [page, search]);

  // WebSocket 메시지 핸들러
  useWebSocket((message) => {
    if (message.type === 'project_updated' || message.type === 'project_created') {
      // 프로젝트가 업데이트되거나 생성되면 목록을 새로고침
      fetchProjects();
      if (message.type === 'project_created') {
        toast.success('새 프로젝트가 생성되었습니다');
      }
    }
  });

  const handleDelete = async (id: string) => {
    if (!confirm('정말로 이 프로젝트를 삭제하시겠습니까?')) return;

    try {
      await projectsService.deleteProject(id);
      toast.success('프로젝트가 삭제되었습니다');
      fetchProjects();
    } catch (error) {
      toast.error('프로젝트 삭제에 실패했습니다');
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
          <h1 className="text-3xl font-bold">프로젝트</h1>
          <p className="text-muted-foreground mt-2">
            AI 모델 학습을 위한 프로젝트를 관리합니다
          </p>
        </div>
        <Button asChild>
          <Link href="/projects/new">
            <Plus className="mr-2 h-4 w-4" />
            새 프로젝트
          </Link>
        </Button>
      </div>

      <div className="flex items-center space-x-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
          <Input
            placeholder="프로젝트 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {loading ? (
        <ProjectsListSkeleton />
      ) : error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>오류</AlertTitle>
          <AlertDescription>
            {error}
            <Button 
              variant="link" 
              className="pl-2" 
              onClick={() => fetchProjects()}
            >
              다시 시도
            </Button>
          </AlertDescription>
        </Alert>
      ) : projects.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <p className="text-muted-foreground mb-4">
              {search ? '검색 결과가 없습니다' : '아직 프로젝트가 없습니다'}
            </p>
            {!search && (
              <Button asChild>
                <Link href="/projects/new">첫 프로젝트 만들기</Link>
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Card key={project.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="line-clamp-1">
                      <Link
                        href={`/projects/${project.id}`}
                        className="hover:underline"
                      >
                        {project.name}
                      </Link>
                    </CardTitle>
                    <CardDescription className="line-clamp-2 mt-2">
                      {project.description || '설명이 없습니다'}
                    </CardDescription>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem asChild>
                        <Link href={`/projects/${project.id}/edit`}>
                          <Edit className="mr-2 h-4 w-4" />
                          편집
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => handleDelete(project.id)}
                        className="text-destructive"
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
                  생성일: {formatDate(project.created_at)}
                </p>
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
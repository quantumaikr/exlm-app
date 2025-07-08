'use client';

import {
    ArrowLeft,
    Bot,
    Database,
    Edit,
    GitBranch,
    Rocket,
    Trash2
} from 'lucide-react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { toast } from 'react-hot-toast';

import { Button } from '@/components/ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import { Project, projectsService } from '@/services/projects';

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!params?.id) {
      router.push('/projects');
      return;
    }

    const fetchProject = async () => {
      try {
        const data = await projectsService.getProject(params.id as string);
        setProject(data);
      } catch (error) {
        toast.error('프로젝트를 불러오는데 실패했습니다');
        router.push('/projects');
      } finally {
        setLoading(false);
      }
    };

    fetchProject();
  }, [params?.id, router]);

  const handleDelete = async () => {
    if (!params?.id) return;
    if (!confirm('정말로 이 프로젝트를 삭제하시겠습니까?')) return;

    try {
      await projectsService.deleteProject(params.id as string);
      toast.success('프로젝트가 삭제되었습니다');
      router.push('/projects');
    } catch (error) {
      toast.error('프로젝트 삭제에 실패했습니다');
    }
  };

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
        <p className="mt-4 text-muted-foreground">로딩 중...</p>
      </div>
    );
  }

  if (!project) {
    return null;
  }

  const quickActions = [
    {
      title: '모델 학습',
      description: '새로운 AI 모델을 학습시킵니다',
      icon: Bot,
      href: `/projects/${project.id}/models/new`,
      color: 'text-blue-600',
    },
    {
      title: '데이터셋 생성',
      description: '학습용 데이터셋을 생성합니다',
      icon: Database,
      href: `/projects/${project.id}/datasets/new`,
      color: 'text-green-600',
    },
    {
      title: '파이프라인 설계',
      description: '학습 파이프라인을 설계합니다',
      icon: GitBranch,
      href: `/projects/${project.id}/pipelines/new`,
      color: 'text-purple-600',
    },
    {
      title: '모델 배포',
      description: '학습된 모델을 배포합니다',
      icon: Rocket,
      href: `/projects/${project.id}/deployments/new`,
      color: 'text-orange-600',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link
            href="/projects"
            className="inline-flex items-center text-sm text-muted-foreground hover:text-primary"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            프로젝트 목록
          </Link>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" asChild>
            <Link href={`/projects/${params?.id}/edit`}>
              <Edit className="mr-2 h-4 w-4" />
              편집
            </Link>
          </Button>
          <Button variant="destructive" onClick={handleDelete}>
            <Trash2 className="mr-2 h-4 w-4" />
            삭제
          </Button>
        </div>
      </div>

      <div>
        <h1 className="text-3xl font-bold">{project.name}</h1>
        {project.description && (
          <p className="text-muted-foreground mt-2">{project.description}</p>
        )}
        <p className="text-sm text-muted-foreground mt-4">
          생성일: {new Date(project.created_at).toLocaleDateString('ko-KR')}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {quickActions.map((action) => {
          const Icon = action.icon;
          return (
            <Card
              key={action.title}
              className="hover:shadow-lg transition-shadow cursor-pointer"
            >
              <Link href={action.href}>
                <CardHeader>
                  <div className="flex items-center space-x-3">
                    <Icon className={`h-8 w-8 ${action.color}`} />
                    <div>
                      <CardTitle>{action.title}</CardTitle>
                      <CardDescription>{action.description}</CardDescription>
                    </div>
                  </div>
                </CardHeader>
              </Link>
            </Card>
          );
        })}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">모델</CardTitle>
            <Bot className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <p className="text-xs text-muted-foreground">학습된 모델</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">데이터셋</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <p className="text-xs text-muted-foreground">생성된 데이터셋</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">파이프라인</CardTitle>
            <GitBranch className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <p className="text-xs text-muted-foreground">실행 중인 파이프라인</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">배포</CardTitle>
            <Rocket className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <p className="text-xs text-muted-foreground">활성 배포</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
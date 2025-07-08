'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Plus, Activity, Database, GitBranch, Rocket } from 'lucide-react';
import Link from 'next/link';
import { SystemStatus } from '@/components/system-status';

const stats = [
  {
    title: '프로젝트',
    value: '0',
    icon: GitBranch,
    href: '/projects',
  },
  {
    title: '모델',
    value: '0',
    icon: Activity,
    href: '/models',
  },
  {
    title: '데이터셋',
    value: '0',
    icon: Database,
    href: '/datasets',
  },
  {
    title: '배포',
    value: '0',
    icon: Rocket,
    href: '/deployments',
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">대시보드</h1>
          <p className="text-muted-foreground mt-2">
            exlm 플랫폼에 오신 것을 환영합니다
          </p>
        </div>
        <Button asChild>
          <Link href="/projects/new">
            <Plus className="mr-2 h-4 w-4" />
            새 프로젝트
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Link key={stat.title} href={stat.href}>
              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    {stat.title}
                  </CardTitle>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stat.value}</div>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>빠른 시작</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button variant="outline" className="w-full justify-start" asChild>
              <Link href="/projects/new">
                <Plus className="mr-2 h-4 w-4" />
                새 프로젝트 생성
              </Link>
            </Button>
            <Button variant="outline" className="w-full justify-start" asChild>
              <Link href="/models">
                <Activity className="mr-2 h-4 w-4" />
                모델 탐색
              </Link>
            </Button>
            <Button variant="outline" className="w-full justify-start" asChild>
              <Link href="/datasets/new">
                <Database className="mr-2 h-4 w-4" />
                데이터셋 생성
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>최근 활동</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground text-sm">
              아직 활동 내역이 없습니다. 새 프로젝트를 시작해보세요!
            </p>
          </CardContent>
        </Card>

        <SystemStatus />
      </div>
    </div>
  );
}
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Database,
  GitBranch,
  Rocket,
  Code2,
  Settings,
  Bot,
} from 'lucide-react';

const menuItems = [
  {
    title: '대시보드',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    title: '프로젝트',
    href: '/projects',
    icon: GitBranch,
  },
  {
    title: '모델',
    href: '/models',
    icon: Bot,
  },
  {
    title: '데이터셋',
    href: '/datasets',
    icon: Database,
  },
  {
    title: '파이프라인',
    href: '/pipelines',
    icon: Code2,
  },
  {
    title: '배포',
    href: '/deployments',
    icon: Rocket,
  },
  {
    title: '설정',
    href: '/settings',
    icon: Settings,
  },
];

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside className={cn('w-64 border-r bg-background', className)}>
      <nav className="flex flex-col space-y-1 p-4">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-accent text-accent-foreground'
                  : 'hover:bg-accent hover:text-accent-foreground'
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{item.title}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
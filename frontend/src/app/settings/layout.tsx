'use client';

import { ReactNode } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { User, Key, Shield, Bell } from 'lucide-react';
import { cn } from '@/lib/utils';

const sidebarItems = [
  {
    title: '프로필',
    href: '/settings/profile',
    icon: User,
  },
  {
    title: 'API 키',
    href: '/settings/api-keys',
    icon: Key,
  },
  {
    title: '보안',
    href: '/settings/security',
    icon: Shield,
  },
  {
    title: '알림',
    href: '/settings/notifications',
    icon: Bell,
  },
];

export default function SettingsLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex gap-8">
      <aside className="w-64">
        <div className="space-y-2">
          <h2 className="text-lg font-semibold mb-4">설정</h2>
          <nav className="space-y-1">
            {sidebarItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                    isActive
                      ? 'bg-secondary text-secondary-foreground'
                      : 'hover:bg-secondary/50'
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.title}
                </Link>
              );
            })}
          </nav>
        </div>
      </aside>
      <main className="flex-1">{children}</main>
    </div>
  );
}
'use client';

import { ReactNode, useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  LayoutDashboard,
  Users,
  FileText,
  AlertTriangle,
  Flag,
  BarChart3,
  Settings,
  Shield,
  LogOut,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/admin', icon: LayoutDashboard },
  { name: 'Athletes', href: '/admin/athletes', icon: Users },
  { name: 'Content', href: '/admin/content', icon: FileText },
  { name: 'Classifications', href: '/admin/classifications', icon: AlertTriangle },
  { name: 'Takedowns', href: '/admin/takedown', icon: Flag },
  { name: 'Analytics', href: '/admin/analytics', icon: BarChart3 },
  { name: 'Settings', href: '/admin/settings', icon: Settings },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  // Public admin routes — render their page directly with no sidebar wrapper.
  const isPublicRoute =
    pathname === '/admin/login' || pathname === '/admin/forgot';

  useEffect(() => {
    if (isPublicRoute) {
      setReady(true);
      return;
    }
    if (typeof window === 'undefined') return;
    if (!apiClient.getStaffToken()) {
      router.replace(`/admin/login?next=${encodeURIComponent(pathname || '/admin')}`);
      return;
    }
    setReady(true);
  }, [isPublicRoute, pathname, router]);

  const meQuery = useQuery({
    queryKey: ['staff-me'],
    queryFn: () => apiClient.getCurrentUser(),
    enabled: ready && !isPublicRoute,
    retry: false,
  });

  useEffect(() => {
    if (meQuery.error) {
      apiClient.clearStaffTokens();
      router.replace(`/admin/login?next=${encodeURIComponent(pathname || '/admin')}`);
    }
  }, [meQuery.error, pathname, router]);

  if (isPublicRoute) return <>{children}</>;
  if (!ready) return null;

  const me = meQuery.data;

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-gray-200">
          <Shield className="w-8 h-8 text-blue-600" />
          <span className="ml-2 text-xl font-bold text-gray-900">FameShield</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = pathname === item.href ||
              (item.href !== '/admin' && pathname?.startsWith(item.href));

            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                  isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                )}
              >
                <item.icon className={cn('w-5 h-5 mr-3', isActive ? 'text-blue-600' : 'text-gray-400')} />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* User Menu */}
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center mb-3">
            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
              <span className="text-sm font-medium text-blue-700">
                {(me?.first_name?.[0] || '?') + (me?.last_name?.[0] || '')}
              </span>
            </div>
            <div className="ml-3 min-w-0">
              <p className="text-sm font-medium text-gray-700 truncate">
                {me ? `${me.first_name} ${me.last_name}` : 'Loading…'}
              </p>
              <p className="text-xs text-gray-500 truncate">{me?.email || ''}</p>
            </div>
          </div>
          <button
            onClick={async () => {
              await apiClient.logout();
              router.replace('/admin/login');
            }}
            className="w-full flex items-center justify-center gap-2 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-md"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">
              {navigation.find(item => pathname === item.href ||
                (item.href !== '/admin' && pathname?.startsWith(item.href)))?.name || 'Dashboard'}
            </h1>
          </div>
          <div className="flex items-center space-x-4">
            <button className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900">
              Notifications
            </button>
            <button className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700">
              + Add Athlete
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto bg-gray-50 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

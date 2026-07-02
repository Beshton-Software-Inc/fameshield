'use client';

import { ReactNode, useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3,
  CreditCard,
  Globe2,
  LayoutDashboard,
  LogOut,
  Shield,
  ShieldAlert,
  UserRound,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { cn } from '@/lib/utils';

const NAV = [
  { name: 'Dashboard', href: '/me', icon: LayoutDashboard },
  { name: 'Profile', href: '/me/profile', icon: UserRound },
  { name: 'Social accounts', href: '/me/social', icon: Globe2 },
  { name: 'Appearances', href: '/me/appearances', icon: BarChart3 },
  { name: 'Violations', href: '/me/violations', icon: ShieldAlert },
  { name: 'Subscription', href: '/me/subscription', icon: CreditCard },
];

export default function PortalLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const token = localStorage.getItem('accessToken');
    if (!token) {
      router.replace('/login');
      return;
    }
    setReady(true);
  }, [router]);

  const meQuery = useQuery({
    queryKey: ['me'],
    queryFn: () => apiClient.getMe(),
    enabled: ready,
    retry: false,
  });

  useEffect(() => {
    if (meQuery.error) {
      apiClient.athleteLogout();
      router.replace('/login');
    }
  }, [meQuery.error, router]);

  if (!ready) return null;

  const me = meQuery.data;

  return (
    <div className="flex h-screen bg-gray-100">
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-gray-200">
          <Shield className="w-8 h-8 text-blue-600" />
          <span className="ml-2 text-xl font-bold text-gray-900">FameShield</span>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV.map((item) => {
            const isActive =
              pathname === item.href || (item.href !== '/me' && pathname?.startsWith(item.href));
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
                <item.icon
                  className={cn('w-5 h-5 mr-3', isActive ? 'text-blue-600' : 'text-gray-400')}
                />
                {item.name}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center mb-3">
            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center overflow-hidden">
              {me?.profile_image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={me.profile_image_url} alt="" className="w-full h-full object-cover" />
              ) : (
                <span className="text-sm font-medium text-blue-700">
                  {(me?.first_name?.[0] || '?') + (me?.last_name?.[0] || '')}
                </span>
              )}
            </div>
            <div className="ml-3 min-w-0">
              <p className="text-sm font-medium text-gray-700 truncate">
                {me?.full_name || 'Athlete'}
              </p>
              <p className="text-xs text-gray-500 truncate">{me?.email || ''}</p>
            </div>
          </div>
          <button
            onClick={() => {
              apiClient.athleteLogout();
              router.replace('/login');
            }}
            className="w-full flex items-center justify-center gap-2 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-md"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-white border-b border-gray-200 flex items-center px-6">
          <h1 className="text-xl font-semibold text-gray-900">
            {NAV.find(
              (n) => pathname === n.href || (n.href !== '/me' && pathname?.startsWith(n.href))
            )?.name || 'Dashboard'}
          </h1>
        </header>
        <main className="flex-1 overflow-y-auto bg-gray-50 p-6">{children}</main>
      </div>
    </div>
  );
}

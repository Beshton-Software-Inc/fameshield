'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { AlertTriangle, BarChart3, CheckCircle2, Globe2 } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { SeverityBadge } from '@/components/severity-badge';
import { formatRelativeTime, getCategoryLabel } from '@/lib/utils';

export default function DashboardPage() {
  const meQuery = useQuery({ queryKey: ['me'], queryFn: () => apiClient.getMe() });
  const subQuery = useQuery({
    queryKey: ['me-subscription'],
    queryFn: () => apiClient.getMySubscription(),
  });
  const appearancesQuery = useQuery({
    queryKey: ['me-appearances'],
    queryFn: () => apiClient.getMyAppearances(),
  });
  const violationsQuery = useQuery({
    queryKey: ['me-violations', 5],
    queryFn: () => apiClient.getMyViolations({ limit: 5 }),
  });

  const me = meQuery.data;
  const sub = subQuery.data;
  const appearances = (appearancesQuery.data as any[]) || [];
  const violations = (violationsQuery.data as any[]) || [];

  const totalContent = appearances.reduce((sum, a) => sum + (a.content_total || 0), 0);
  const totalFlagged = appearances.reduce((sum, a) => sum + (a.flagged_total || 0), 0);
  const totalHigh = appearances.reduce((sum, a) => sum + (a.high_severity_total || 0), 0);

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-1">
          Welcome back{me ? `, ${me.first_name}` : ''}.
        </h2>
        <p className="text-sm text-gray-500">
          {sub
            ? `${sub.product_name} plan · ${sub.billing_interval}ly billing · ${sub.status}`
            : 'You are not subscribed yet.'}{' '}
          {sub && sub.cancel_at_period_end && (
            <span className="text-yellow-700 font-medium">
              Scheduled to cancel at period end.
            </span>
          )}
        </p>
        {!sub && (
          <Link
            href="/me/subscription"
            className="mt-3 inline-block px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Choose a plan
          </Link>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard icon={BarChart3} label="Content tracked" value={totalContent} tone="gray" />
        <StatCard icon={AlertTriangle} label="Flagged" value={totalFlagged} tone="orange" />
        <StatCard icon={CheckCircle2} label="High severity (3+)" value={totalHigh} tone="red" />
      </div>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900">Where you appear</h3>
          <Link href="/me/social" className="text-sm text-blue-600 hover:text-blue-800">
            Manage accounts →
          </Link>
        </div>
        <div className="bg-white rounded-lg border border-gray-200">
          {appearances.length === 0 ? (
            <div className="p-8 text-center">
              <Globe2 className="w-8 h-8 text-gray-300 mx-auto mb-2" />
              <p className="text-sm text-gray-500">
                No platforms tracked yet. Connect your social handles to start monitoring.
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {appearances.map((a) => (
                <li key={a.platform} className="flex items-center justify-between px-4 py-3">
                  <div>
                    <p className="text-sm font-medium text-gray-900 capitalize">{a.platform}</p>
                    <p className="text-xs text-gray-500">
                      {a.content_total} items · {a.flagged_total} flagged · {a.high_severity_total} high
                    </p>
                  </div>
                  <p className="text-xs text-gray-500">
                    {a.last_seen_at ? `Last seen ${formatRelativeTime(a.last_seen_at)}` : '—'}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900">Recent violations</h3>
          <Link href="/me/violations" className="text-sm text-blue-600 hover:text-blue-800">
            View all →
          </Link>
        </div>
        <div className="bg-white rounded-lg border border-gray-200">
          {violations.length === 0 ? (
            <div className="p-8 text-center">
              <CheckCircle2 className="w-8 h-8 text-green-300 mx-auto mb-2" />
              <p className="text-sm text-gray-500">No violations detected. Keep it up.</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {violations.map((v) => (
                <li key={v.id} className="px-4 py-3">
                  <div className="flex items-center gap-2 mb-1">
                    <SeverityBadge severity={v.severity_level} />
                    <span className="text-sm font-medium text-gray-900">
                      {getCategoryLabel(v.primary_category)}
                    </span>
                    <span className="text-xs text-gray-500 capitalize">· {v.platform}</span>
                  </div>
                  <p className="text-sm text-gray-700 line-clamp-2">{v.reasoning}</p>
                  <p className="text-xs text-gray-500 mt-1">{formatRelativeTime(v.created_at)}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: any;
  label: string;
  value: number;
  tone: 'gray' | 'orange' | 'red';
}) {
  const toneClass = {
    gray: 'text-gray-500',
    orange: 'text-orange-600',
    red: 'text-red-600',
  }[tone];
  return (
    <div className="bg-white p-4 rounded-lg border border-gray-200 flex items-center">
      <div className={`p-2 rounded-md bg-gray-50 ${toneClass}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="ml-3">
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold text-gray-900 tabular-nums">{value}</p>
      </div>
    </div>
  );
}

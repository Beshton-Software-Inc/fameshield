'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ChevronDown } from 'lucide-react';
import Link from 'next/link';
import { apiClient } from '@/lib/api-client';
import { SeverityBadge } from '@/components/severity-badge';
import { formatDate, formatRelativeTime, getCategoryLabel } from '@/lib/utils';

function groupByDay<T extends { created_at: string }>(items: T[]): [string, T[]][] {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const key = new Date(item.created_at).toISOString().slice(0, 10);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(item);
  }
  return Array.from(groups.entries()).sort(([a], [b]) => (a < b ? 1 : -1));
}

export default function ClassificationsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['classifications', 'timeline'],
    queryFn: () => apiClient.getClassifications({ limit: 200 }),
  });
  const { data: athletes } = useQuery({
    queryKey: ['athletes'],
    queryFn: () => apiClient.getAthletes({ limit: 200 }),
  });

  const athleteMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const a of (athletes as any[]) || []) map.set(a.id, a.full_name);
    return map;
  }, [athletes]);

  const groups = useMemo(() => groupByDay((data as any[]) || []), [data]);
  const items = (data as any[]) || [];

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900">
            {isLoading ? 'Loading classifications…' : `${items.length} classifications`}
          </h2>
          <span className="text-xs text-gray-500">Newest first, grouped by day</span>
        </div>

        {error && (
          <div className="p-4 text-sm text-red-600">
            Could not load classifications. Sign in required.
          </div>
        )}

        {!isLoading && !error && items.length === 0 && (
          <div className="p-8 text-center">
            <AlertTriangle className="w-8 h-8 text-gray-300 mx-auto mb-2" />
            <p className="text-sm text-gray-500">
              No classifications yet. They will appear here as content is analyzed.
            </p>
          </div>
        )}

        <ul className="divide-y divide-gray-100">
          {groups.map(([day, dayItems]) => (
            <li key={day}>
              <div className="px-4 py-2 bg-gray-50 border-b border-gray-100 sticky top-0">
                <div className="flex items-baseline justify-between">
                  <h3 className="text-sm font-semibold text-gray-900">
                    {formatDayHeading(day)}
                  </h3>
                  <span className="text-xs text-gray-500">
                    {dayItems.length} classification{dayItems.length === 1 ? '' : 's'}
                  </span>
                </div>
              </div>
              <ul className="divide-y divide-gray-100">
                {dayItems.map((c: any) => (
                  <li key={c.id} className="px-4 py-3 hover:bg-gray-50">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <SeverityBadge severity={c.severity_level} />
                          <span className="text-sm font-medium text-gray-900">
                            {getCategoryLabel(c.primary_category)}
                          </span>
                          {c.status && (
                            <span className="text-xs text-gray-500 capitalize">
                              · {c.status.replace(/_/g, ' ')}
                            </span>
                          )}
                          {!c.human_reviewed && c.severity_level >= 4 && (
                            <span className="text-xs font-medium text-yellow-700">
                              · Needs review
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-700 line-clamp-2">{c.reasoning}</p>
                        <div className="mt-1 text-xs text-gray-500">
                          {athleteMap.get(c.athlete_id) || 'Unknown athlete'} ·{' '}
                          {(c.confidence_score * 100).toFixed(0)}% confidence
                        </div>
                      </div>
                      <div className="flex flex-col items-end shrink-0">
                        <span className="text-xs text-gray-500" title={formatDate(c.created_at)}>
                          {formatRelativeTime(c.created_at)}
                        </span>
                        <Link
                          href={`/admin/content/${c.content_item_id}`}
                          className="mt-2 text-xs font-medium text-blue-600 hover:text-blue-800"
                        >
                          View content →
                        </Link>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>

        {isLoading && (
          <div className="p-8 flex justify-center">
            <ChevronDown className="w-6 h-6 text-gray-300 animate-bounce" />
          </div>
        )}
      </div>
    </div>
  );
}

function formatDayHeading(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

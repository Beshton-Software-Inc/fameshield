'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { ExternalLink, FileText } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { SeverityBadge } from '@/components/severity-badge';
import { formatDate, formatRelativeTime, getCategoryLabel, truncateText } from '@/lib/utils';

function groupByDay<T extends { discovered_at: string }>(items: T[]): [string, T[]][] {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const key = new Date(item.discovered_at).toISOString().slice(0, 10);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(item);
  }
  return Array.from(groups.entries()).sort(([a], [b]) => (a < b ? 1 : -1));
}

export default function ContentPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['content', 'timeline'],
    queryFn: () => apiClient.getContent({ limit: 200 }),
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

  const items = (data as any[]) || [];
  const groups = useMemo(() => groupByDay(items), [items]);

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900">
            {isLoading ? 'Loading content…' : `${items.length} content items`}
          </h2>
          <span className="text-xs text-gray-500">Newest first, grouped by day</span>
        </div>

        {error && (
          <div className="p-4 text-sm text-red-600">
            Could not load content. Sign in required.
          </div>
        )}

        {!isLoading && !error && items.length === 0 && (
          <div className="p-8 text-center">
            <FileText className="w-8 h-8 text-gray-300 mx-auto mb-2" />
            <p className="text-sm text-gray-500">
              No content captured yet. Monitored posts and comments will appear here.
            </p>
          </div>
        )}

        <ul className="divide-y divide-gray-100">
          {groups.map(([day, dayItems]) => (
            <li key={day}>
              <div className="px-4 py-2 bg-gray-50 border-b border-gray-100 sticky top-0">
                <div className="flex items-baseline justify-between">
                  <h3 className="text-sm font-semibold text-gray-900">{formatDayHeading(day)}</h3>
                  <span className="text-xs text-gray-500">
                    {dayItems.length} item{dayItems.length === 1 ? '' : 's'}
                  </span>
                </div>
              </div>
              <ul className="divide-y divide-gray-100">
                {dayItems.map((item: any) => (
                  <li key={item.id} className="px-4 py-3 hover:bg-gray-50">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          {item.classification?.severity_level != null && (
                            <SeverityBadge severity={item.classification.severity_level} />
                          )}
                          {item.classification?.primary_category && (
                            <span className="text-sm font-medium text-gray-900">
                              {getCategoryLabel(item.classification.primary_category)}
                            </span>
                          )}
                          <span className="text-xs text-gray-500 capitalize">
                            · {item.platform}
                          </span>
                          <span className="text-xs text-gray-500">· @{item.author_username}</span>
                        </div>
                        <p className="text-sm text-gray-700 whitespace-pre-line">
                          {truncateText(item.content_text || '', 240)}
                        </p>
                        <div className="mt-1 text-xs text-gray-500">
                          {athleteMap.get(item.athlete_id) || 'Unknown athlete'}
                          {item.evidence_count > 0 && (
                            <span> · {item.evidence_count} evidence</span>
                          )}
                        </div>
                      </div>
                      <div className="flex flex-col items-end shrink-0">
                        <span className="text-xs text-gray-500" title={formatDate(item.discovered_at)}>
                          {formatRelativeTime(item.discovered_at)}
                        </span>
                        <div className="mt-2 flex items-center gap-3">
                          {item.content_url && (
                            <a
                              href={item.content_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center text-xs text-gray-500 hover:text-gray-800"
                            >
                              Source
                              <ExternalLink className="w-3 h-3 ml-0.5" />
                            </a>
                          )}
                          <Link
                            href={`/admin/content/${item.id}`}
                            className="text-xs font-medium text-blue-600 hover:text-blue-800"
                          >
                            Details →
                          </Link>
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
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

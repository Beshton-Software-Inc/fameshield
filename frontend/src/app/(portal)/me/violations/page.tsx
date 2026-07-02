'use client';

import { useQuery } from '@tanstack/react-query';
import { ExternalLink, ShieldAlert } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { SeverityBadge } from '@/components/severity-badge';
import { formatDate, formatRelativeTime, getCategoryLabel, truncateText } from '@/lib/utils';

export default function ViolationsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['me-violations'],
    queryFn: () => apiClient.getMyViolations({ limit: 200 }),
  });

  const items = (data as any[]) || [];

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">
          {isLoading ? 'Loading…' : `${items.length} violations detected`}
        </h2>
      </div>

      {!isLoading && items.length === 0 && (
        <div className="p-8 text-center">
          <ShieldAlert className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">
            No violations yet. Any harmful content flagged about you will appear here.
          </p>
        </div>
      )}

      <ul className="divide-y divide-gray-100">
        {items.map((v: any) => (
          <li key={v.id} className="px-4 py-3 hover:bg-gray-50">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <SeverityBadge severity={v.severity_level} />
                  <span className="text-sm font-medium text-gray-900">
                    {getCategoryLabel(v.primary_category)}
                  </span>
                  <span className="text-xs text-gray-500 capitalize">· {v.platform}</span>
                  <span className="text-xs text-gray-500">· @{v.author_username}</span>
                </div>
                {v.content_excerpt && (
                  <p className="text-sm text-gray-700 whitespace-pre-line">
                    {truncateText(v.content_excerpt, 240)}
                  </p>
                )}
                <p className="text-xs text-gray-500 mt-1">
                  <span className="font-medium">AI reasoning:</span> {truncateText(v.reasoning, 200)}
                </p>
              </div>
              <div className="flex flex-col items-end shrink-0">
                <span className="text-xs text-gray-500" title={formatDate(v.created_at)}>
                  {formatRelativeTime(v.created_at)}
                </span>
                {v.content_url && (
                  <a
                    href={v.content_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 inline-flex items-center text-xs text-gray-500 hover:text-gray-800"
                  >
                    Source
                    <ExternalLink className="w-3 h-3 ml-0.5" />
                  </a>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

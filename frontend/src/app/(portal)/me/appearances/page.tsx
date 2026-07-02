'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { formatRelativeTime } from '@/lib/utils';

export default function AppearancesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['me-appearances'],
    queryFn: () => apiClient.getMyAppearances(),
  });

  const rows = (data as any[]) || [];

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-200">
        <h2 className="text-sm font-semibold text-gray-900">Appearances per platform</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <Th>Platform</Th>
              <Th align="right">Content</Th>
              <Th align="right">Flagged</Th>
              <Th align="right">High severity</Th>
              <Th>Last seen</Th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {rows.map((r: any) => (
              <tr key={r.platform} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm font-medium text-gray-900 capitalize">
                  {r.platform}
                </td>
                <td className="px-4 py-3 text-sm text-gray-900 text-right tabular-nums">
                  {r.content_total}
                </td>
                <td className="px-4 py-3 text-sm text-gray-900 text-right tabular-nums">
                  {r.flagged_total}
                </td>
                <td className="px-4 py-3 text-sm text-gray-900 text-right tabular-nums">
                  {r.high_severity_total}
                </td>
                <td className="px-4 py-3 text-sm text-gray-500">
                  {r.last_seen_at ? formatRelativeTime(r.last_seen_at) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!isLoading && rows.length === 0 && (
          <div className="p-8 text-center">
            <p className="text-sm text-gray-500">
              No content has been captured yet. Connect a social account to start monitoring.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function Th({
  children,
  align,
}: {
  children: React.ReactNode;
  align?: 'right';
}) {
  return (
    <th
      className={`px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${
        align === 'right' ? 'text-right' : 'text-left'
      }`}
    >
      {children}
    </th>
  );
}

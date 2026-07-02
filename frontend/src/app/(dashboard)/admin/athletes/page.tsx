'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { ArrowDown, ArrowUp, ArrowUpDown, Search } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { cn, formatRelativeTime, getCategoryLabel } from '@/lib/utils';

const CATEGORY_FILTERS = [
  { value: 'all', label: 'All Cases' },
  { value: 'threat_of_violence', label: 'Threat of Violence' },
  { value: 'doxxing', label: 'Doxxing' },
  { value: 'hate_speech', label: 'Hate Speech' },
  { value: 'sexual_harassment', label: 'Sexual Harassment' },
  { value: 'harassment', label: 'Harassment' },
  { value: 'coordinated_attack', label: 'Coordinated Attack' },
  { value: 'deepfake', label: 'Deepfake' },
  { value: 'impersonation', label: 'Impersonation' },
];

const RISK_COLORS: Record<string, string> = {
  low: 'bg-gray-100 text-gray-700',
  medium: 'bg-yellow-100 text-yellow-700',
  high: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-100 text-red-700',
};

type SortKey = 'name' | 'sport' | 'risk' | 'classifications' | 'content' | 'last_monitored';
type SortDir = 'asc' | 'desc';

interface Row {
  id: string;
  full_name: string;
  sport: string;
  risk_level: string;
  monitoring_enabled: boolean;
  last_monitored_at: string | null;
  classifications_total: number;
  content_total: number;
  categories: Set<string>;
}

export default function AthletesPage() {
  const [nameQuery, setNameQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  const athletesQuery = useQuery({
    queryKey: ['athletes'],
    queryFn: () => apiClient.getAthletes({ limit: 200 }),
  });
  const classificationsQuery = useQuery({
    queryKey: ['classifications', 'all-for-athletes'],
    queryFn: () => apiClient.getClassifications({ limit: 1000 }),
  });
  const contentQuery = useQuery({
    queryKey: ['content', 'all-for-athletes'],
    queryFn: () => apiClient.getContent({ limit: 1000 }),
  });

  const isLoading =
    athletesQuery.isLoading || classificationsQuery.isLoading || contentQuery.isLoading;
  const error = athletesQuery.error || classificationsQuery.error || contentQuery.error;

  const rows: Row[] = useMemo(() => {
    const athletes: any[] = athletesQuery.data || [];
    const classifications: any[] = classificationsQuery.data || [];
    const content: any[] = contentQuery.data || [];

    const classByAthlete = new Map<string, { count: number; cats: Set<string> }>();
    for (const c of classifications) {
      const entry = classByAthlete.get(c.athlete_id) || { count: 0, cats: new Set() };
      entry.count += 1;
      if (c.primary_category) entry.cats.add(c.primary_category);
      classByAthlete.set(c.athlete_id, entry);
    }

    const contentByAthlete = new Map<string, number>();
    for (const item of content) {
      contentByAthlete.set(item.athlete_id, (contentByAthlete.get(item.athlete_id) || 0) + 1);
    }

    return athletes.map((a: any) => ({
      id: a.id,
      full_name: a.full_name,
      sport: a.sport,
      risk_level: a.risk_level,
      monitoring_enabled: a.monitoring_enabled,
      last_monitored_at: a.last_monitored_at,
      classifications_total: classByAthlete.get(a.id)?.count ?? 0,
      content_total: contentByAthlete.get(a.id) ?? 0,
      categories: classByAthlete.get(a.id)?.cats ?? new Set<string>(),
    }));
  }, [athletesQuery.data, classificationsQuery.data, contentQuery.data]);

  const filtered = useMemo(() => {
    const q = nameQuery.trim().toLowerCase();
    return rows.filter((r) => {
      if (q && !r.full_name.toLowerCase().includes(q)) return false;
      if (categoryFilter !== 'all' && !r.categories.has(categoryFilter)) return false;
      return true;
    });
  }, [rows, nameQuery, categoryFilter]);

  const sorted = useMemo(() => {
    const list = [...filtered];
    const cmp = (a: Row, b: Row): number => {
      switch (sortKey) {
        case 'name':
          return a.full_name.localeCompare(b.full_name);
        case 'sport':
          return (a.sport || '').localeCompare(b.sport || '');
        case 'risk': {
          const order = ['low', 'medium', 'high', 'critical'];
          return order.indexOf(a.risk_level) - order.indexOf(b.risk_level);
        }
        case 'classifications':
          return a.classifications_total - b.classifications_total;
        case 'content':
          return a.content_total - b.content_total;
        case 'last_monitored': {
          const at = a.last_monitored_at ? new Date(a.last_monitored_at).getTime() : 0;
          const bt = b.last_monitored_at ? new Date(b.last_monitored_at).getTime() : 0;
          return at - bt;
        }
      }
    };
    list.sort((a, b) => (sortDir === 'asc' ? cmp(a, b) : -cmp(a, b)));
    return list;
  }, [filtered, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-4 rounded-lg border border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">Search by name</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={nameQuery}
                onChange={(e) => setNameQuery(e.target.value)}
                placeholder="Type an athlete name..."
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Filter by case</label>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {CATEGORY_FILTERS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900">
            {isLoading ? 'Loading athletes…' : `${sorted.length} of ${rows.length} athletes`}
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <SortableTh label="Name" active={sortKey === 'name'} dir={sortDir} onClick={() => toggleSort('name')} />
                <SortableTh label="Sport" active={sortKey === 'sport'} dir={sortDir} onClick={() => toggleSort('sport')} />
                <SortableTh label="Risk Level" active={sortKey === 'risk'} dir={sortDir} onClick={() => toggleSort('risk')} />
                <SortableTh
                  label="Classifications"
                  active={sortKey === 'classifications'}
                  dir={sortDir}
                  onClick={() => toggleSort('classifications')}
                  className="text-right"
                />
                <SortableTh
                  label="Content"
                  active={sortKey === 'content'}
                  dir={sortDir}
                  onClick={() => toggleSort('content')}
                  className="text-right"
                />
                <SortableTh
                  label="Last Monitored"
                  active={sortKey === 'last_monitored'}
                  dir={sortDir}
                  onClick={() => toggleSort('last_monitored')}
                />
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sorted.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap">
                    <Link
                      href={`/admin/athletes/${r.id}`}
                      className="text-sm font-medium text-blue-600 hover:text-blue-800"
                    >
                      {r.full_name}
                    </Link>
                    {!r.monitoring_enabled && (
                      <span className="ml-2 text-xs text-gray-400">(paused)</span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">{r.sport}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span
                      className={cn(
                        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize',
                        RISK_COLORS[r.risk_level] || 'bg-gray-100 text-gray-700'
                      )}
                    >
                      {r.risk_level}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right tabular-nums">
                    {r.classifications_total}
                    {r.categories.size > 0 && (
                      <span
                        className="ml-2 text-xs text-gray-400"
                        title={Array.from(r.categories).map(getCategoryLabel).join(', ')}
                      >
                        ({r.categories.size} case{r.categories.size === 1 ? '' : 's'})
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right tabular-nums">
                    {r.content_total}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                    {r.last_monitored_at ? formatRelativeTime(r.last_monitored_at) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!isLoading && sorted.length === 0 && (
            <div className="text-center py-12">
              <p className="text-sm text-gray-500">
                {rows.length === 0
                  ? error
                    ? 'Could not load athletes. Sign in required.'
                    : 'No athletes yet. Add one from the header to get started.'
                  : 'No athletes match the current filters.'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SortableTh({
  label,
  active,
  dir,
  onClick,
  className,
}: {
  label: string;
  active: boolean;
  dir: SortDir;
  onClick: () => void;
  className?: string;
}) {
  const Icon = !active ? ArrowUpDown : dir === 'asc' ? ArrowUp : ArrowDown;
  return (
    <th
      scope="col"
      className={cn(
        'px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider select-none',
        className
      )}
    >
      <button
        type="button"
        onClick={onClick}
        className={cn(
          'inline-flex items-center gap-1 hover:text-gray-900',
          active && 'text-gray-900'
        )}
      >
        {label}
        <Icon className="w-3.5 h-3.5" />
      </button>
    </th>
  );
}

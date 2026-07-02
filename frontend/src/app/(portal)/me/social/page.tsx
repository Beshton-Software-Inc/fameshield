'use client';

import { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Trash2 } from 'lucide-react';
import { apiClient } from '@/lib/api-client';

const PLATFORMS = [
  { value: 'twitter', label: 'Twitter / X' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'tiktok', label: 'TikTok' },
  { value: 'youtube', label: 'YouTube' },
  { value: 'facebook', label: 'Facebook' },
];

export default function SocialAccountsPage() {
  const qc = useQueryClient();
  const listQuery = useQuery({
    queryKey: ['me-social'],
    queryFn: () => apiClient.getMySocialAccounts(),
  });

  const [platform, setPlatform] = useState('twitter');
  const [username, setUsername] = useState('');
  const [error, setError] = useState<string | null>(null);

  const addMutation = useMutation({
    mutationFn: () => apiClient.addMySocialAccount({ platform, username }),
    onSuccess: () => {
      setUsername('');
      setError(null);
      qc.invalidateQueries({ queryKey: ['me-social'] });
    },
    onError: (err: any) => {
      setError(err?.response?.data?.detail || err?.message || 'Failed to add account');
    },
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => apiClient.removeMySocialAccount(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me-social'] }),
  });

  const accounts = (listQuery.data as any[]) || [];

  function onAdd(e: FormEvent) {
    e.preventDefault();
    if (!username.trim()) return;
    addMutation.mutate();
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Add a social account</h2>
        <form onSubmit={onAdd} className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {PLATFORMS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="md:col-span-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={addMutation.isPending}
            className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
          >
            {addMutation.isPending ? 'Adding…' : 'Add account'}
          </button>
        </form>
        {error && (
          <p className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
            {error}
          </p>
        )}
      </div>

      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <h2 className="text-sm font-semibold text-gray-900">Your accounts</h2>
        </div>
        {listQuery.isLoading ? (
          <p className="p-6 text-sm text-gray-500">Loading…</p>
        ) : accounts.length === 0 ? (
          <p className="p-6 text-sm text-gray-500">No social accounts connected yet.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {accounts.map((a: any) => (
              <li key={a.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-gray-900 capitalize">
                    {a.platform} · @{a.username}
                  </p>
                  <p className="text-xs text-gray-500">
                    {a.follower_count?.toLocaleString() || 0} followers · {a.monitoring_status}
                  </p>
                </div>
                <button
                  onClick={() => removeMutation.mutate(a.id)}
                  disabled={removeMutation.isPending}
                  className="p-2 text-gray-400 hover:text-red-600 rounded-md"
                  aria-label="Remove"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

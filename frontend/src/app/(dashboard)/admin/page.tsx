'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { ClassificationCard } from '@/components/classification-card';
import { Filter, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

const SEVERITY_FILTERS = [
  { value: 'all', label: 'All Severity' },
  { value: '5', label: 'Urgent' },
  { value: '4', label: 'Critical' },
  { value: '3', label: 'High' },
  { value: '2', label: 'Medium' },
  { value: '1', label: 'Low' },
];

const CATEGORY_FILTERS = [
  { value: 'all', label: 'All Categories' },
  { value: 'threat_of_violence', label: 'Threat of Violence' },
  { value: 'doxxing', label: 'Doxxing' },
  { value: 'hate_speech', label: 'Hate Speech' },
  { value: 'sexual_harassment', label: 'Sexual Harassment' },
  { value: 'harassment', label: 'Harassment' },
  { value: 'coordinated_attack', label: 'Coordinated Attack' },
  { value: 'deepfake', label: 'Deepfake' },
  { value: 'impersonation', label: 'Impersonation' },
];

const STATUS_FILTERS = [
  { value: 'all', label: 'All Status' },
  { value: 'needs_review', label: 'Needs Review' },
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'false_positive', label: 'False Positive' },
  { value: 'escalated', label: 'Escalated' },
];

export default function AdminDashboard() {
  const [severityFilter, setSeverityFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  // Fetch classifications
  const { data: classifications, isLoading, error, refetch } = useQuery({
    queryKey: ['classifications', severityFilter, categoryFilter, statusFilter],
    queryFn: async () => {
      const params: Record<string, any> = {};

      if (severityFilter !== 'all') {
        params.severity_min = parseInt(severityFilter);
        params.severity_max = parseInt(severityFilter);
      }

      if (categoryFilter !== 'all') {
        params.category = categoryFilter;
      }

      if (statusFilter === 'needs_review') {
        params.requires_review = true;
      } else if (statusFilter !== 'all') {
        params.status = statusFilter;
      }

      params.limit = 50;

      return apiClient.getClassifications(params);
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch content items for classifications
  const { data: contentItems } = useQuery({
    queryKey: ['content-items', classifications?.map((c: any) => c.content_item_id)],
    queryFn: async () => {
      if (!classifications || classifications.length === 0) return {};

      const items: Record<string, any> = {};
      for (const classification of classifications.slice(0, 20)) {
        try {
          const item = await apiClient.getContentItem(classification.content_item_id);
          items[classification.content_item_id] = item;
        } catch (err) {
          console.error('Failed to fetch content item:', err);
        }
      }
      return items;
    },
    enabled: !!classifications && classifications.length > 0,
  });

  // Fetch athletes for context
  const { data: athletes } = useQuery({
    queryKey: ['athletes'],
    queryFn: () => apiClient.getAthletes(),
  });

  const athleteMap = athletes?.reduce((acc: Record<string, any>, athlete: any) => {
    acc[athlete.id] = athlete;
    return acc;
  }, {}) || {};

  return (
    <div className="space-y-6">
      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <p className="text-sm text-gray-500">Total Classifications</p>
          <p className="text-2xl font-bold text-gray-900">{classifications?.length || 0}</p>
        </div>
        <div className="bg-white p-4 rounded-lg border border-red-200 bg-red-50">
          <p className="text-sm text-red-600">Needs Review</p>
          <p className="text-2xl font-bold text-red-700">
            {classifications?.filter((c: any) => !c.human_reviewed && c.severity_level >= 4).length || 0}
          </p>
        </div>
        <div className="bg-white p-4 rounded-lg border border-orange-200 bg-orange-50">
          <p className="text-sm text-orange-600">High Severity (3+)</p>
          <p className="text-2xl font-bold text-orange-700">
            {classifications?.filter((c: any) => c.severity_level >= 3).length || 0}
          </p>
        </div>
        <div className="bg-white p-4 rounded-lg border border-green-200 bg-green-50">
          <p className="text-sm text-green-600">Active Athletes</p>
          <p className="text-2xl font-bold text-green-700">
            {athletes?.filter((a: any) => a.monitoring_enabled).length || 0}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Filter className="w-5 h-5 text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900">Filters</h2>
          </div>
          <button
            onClick={() => refetch()}
            className="flex items-center px-3 py-1.5 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50 rounded-md"
          >
            <RefreshCw className="w-4 h-4 mr-1" />
            Refresh
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Severity Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Severity Level
            </label>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {SEVERITY_FILTERS.map((filter) => (
                <option key={filter.value} value={filter.value}>
                  {filter.label}
                </option>
              ))}
            </select>
          </div>

          {/* Category Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Category
            </label>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {CATEGORY_FILTERS.map((filter) => (
                <option key={filter.value} value={filter.value}>
                  {filter.label}
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Review Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {STATUS_FILTERS.map((filter) => (
                <option key={filter.value} value={filter.value}>
                  {filter.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Classification Feed */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Classifications</h2>

        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-8 h-8 text-gray-400 animate-spin" />
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
            <p className="text-red-700">Failed to load classifications. Please try again.</p>
          </div>
        )}

        {!isLoading && !error && classifications && classifications.length === 0 && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
            <p className="text-gray-500">No classifications found matching your filters.</p>
          </div>
        )}

        {!isLoading && !error && classifications && classifications.length > 0 && (
          <div className="space-y-4">
            {classifications.map((classification: any) => (
              <ClassificationCard
                key={classification.id}
                classification={classification}
                contentItem={contentItems?.[classification.content_item_id]}
                athleteName={athleteMap[classification.athlete_id]?.name}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

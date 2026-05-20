import { formatRelativeTime, getCategoryLabel, truncateText } from '@/lib/utils';
import { SeverityBadge } from './severity-badge';
import { ExternalLink, AlertCircle } from 'lucide-react';
import Link from 'next/link';

interface ClassificationCardProps {
  classification: {
    id: string;
    content_item_id: string;
    athlete_id: string;
    primary_category: string;
    severity_level: number;
    confidence_score: number;
    reasoning: string;
    human_reviewed: boolean;
    created_at: string;
  };
  contentItem?: {
    content_text: string;
    author_username: string;
    platform: string;
    content_url: string;
  };
  athleteName?: string;
}

export function ClassificationCard({
  classification,
  contentItem,
  athleteName
}: ClassificationCardProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-2">
          <SeverityBadge severity={classification.severity_level} />
          <span className="text-sm font-medium text-gray-900">
            {getCategoryLabel(classification.primary_category)}
          </span>
          {!classification.human_reviewed && classification.severity_level >= 4 && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
              <AlertCircle className="w-3 h-3 mr-1" />
              Needs Review
            </span>
          )}
        </div>
        <span className="text-xs text-gray-500">
          {formatRelativeTime(classification.created_at)}
        </span>
      </div>

      {contentItem && (
        <>
          <p className="text-sm text-gray-700 mb-3">
            {truncateText(contentItem.content_text, 200)}
          </p>

          <div className="flex items-center justify-between text-xs text-gray-500 mb-3">
            <div className="flex items-center space-x-3">
              <span>@{contentItem.author_username}</span>
              <span className="capitalize">{contentItem.platform}</span>
              {athleteName && <span>• {athleteName}</span>}
            </div>
            <a
              href={contentItem.content_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center text-blue-600 hover:text-blue-800"
            >
              View Original
              <ExternalLink className="w-3 h-3 ml-1" />
            </a>
          </div>
        </>
      )}

      <div className="border-t border-gray-100 pt-3">
        <p className="text-xs text-gray-600 mb-2">
          <span className="font-medium">AI Reasoning:</span> {truncateText(classification.reasoning, 150)}
        </p>
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">
            Confidence: {(classification.confidence_score * 100).toFixed(1)}%
          </span>
          <Link
            href={`/admin/content/${classification.content_item_id}`}
            className="text-xs font-medium text-blue-600 hover:text-blue-800"
          >
            View Details →
          </Link>
        </div>
      </div>
    </div>
  );
}

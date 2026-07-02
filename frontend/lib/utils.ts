/**
 * Utility functions
 */
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatRelativeTime(date: string | Date): string {
  const now = new Date();
  const then = new Date(date);
  const diffInSeconds = Math.floor((now.getTime() - then.getTime()) / 1000);

  if (diffInSeconds < 60) return 'just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;

  return formatDate(date);
}

export function getSeverityColor(severity: number): string {
  switch (severity) {
    case 1:
      return 'bg-gray-100 text-gray-800 border-gray-300';
    case 2:
      return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    case 3:
      return 'bg-orange-100 text-orange-800 border-orange-300';
    case 4:
      return 'bg-red-100 text-red-800 border-red-300';
    case 5:
      return 'bg-purple-100 text-purple-800 border-purple-300';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-300';
  }
}

export function getSeverityLabel(severity: number): string {
  switch (severity) {
    case 1:
      return 'Low';
    case 2:
      return 'Medium';
    case 3:
      return 'High';
    case 4:
      return 'Critical';
    case 5:
      return 'Urgent';
    default:
      return 'Unknown';
  }
}

export function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    normal_criticism: 'Normal Criticism',
    harassment: 'Harassment',
    hate_speech: 'Hate Speech',
    sexual_harassment: 'Sexual Harassment',
    threat_of_violence: 'Threat of Violence',
    doxxing: 'Doxxing',
    impersonation: 'Impersonation',
    fake_quote: 'Fake Quote',
    fake_endorsement: 'Fake Endorsement',
    deepfake: 'Deepfake',
    coordinated_attack: 'Coordinated Attack',
    gambling_abuse: 'Gambling Abuse',
  };
  return labels[category] || category;
}

export function truncateText(text: string, maxLength: number = 100): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

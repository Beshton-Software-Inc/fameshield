import { cn, getSeverityLabel, getSeverityColor } from '@/lib/utils';

interface SeverityBadgeProps {
  severity: number;
  className?: string;
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
        getSeverityColor(severity),
        className
      )}
    >
      {getSeverityLabel(severity)}
    </span>
  );
}

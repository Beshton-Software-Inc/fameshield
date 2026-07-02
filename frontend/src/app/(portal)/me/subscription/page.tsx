'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CalendarClock, Check, CircleDollarSign, X } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { cn, formatDate } from '@/lib/utils';

type Interval = 'month' | 'year';

interface Product {
  id: string;
  slug: string;
  name: string;
  description: string;
  price_monthly_cents: number;
  price_yearly_cents: number;
  currency: string;
  features: string[];
}

interface Subscription {
  id: string;
  product_id: string;
  product_slug: string;
  product_name: string;
  billing_interval: Interval;
  status: string;
  amount_cents: number;
  currency: string;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  canceled_at: string | null;
}

function money(cents: number, currency = 'USD') {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
  }).format(cents / 100);
}

export default function SubscriptionPage() {
  const qc = useQueryClient();
  const [interval, setInterval] = useState<Interval>('month');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const productsQuery = useQuery<Product[]>({
    queryKey: ['products'],
    queryFn: () => apiClient.getProducts(),
  });

  const subQuery = useQuery<Subscription | null>({
    queryKey: ['me-subscription'],
    queryFn: () => apiClient.getMySubscription(),
  });

  const products = productsQuery.data || [];
  const currentSub = subQuery.data;
  const currentProduct = useMemo(
    () => products.find((p) => p.id === currentSub?.product_id) || null,
    [products, currentSub]
  );

  function invalidate() {
    qc.invalidateQueries({ queryKey: ['me-subscription'] });
  }

  const subscribeMutation = useMutation({
    mutationFn: (p: Product) => apiClient.subscribe(p.id, interval),
    onSuccess: () => {
      setError(null);
      setNotice('Subscription started.');
      invalidate();
    },
    onError: (err: any) => setError(err?.response?.data?.detail || 'Could not start subscription'),
  });

  const changeMutation = useMutation({
    mutationFn: (p: Product) => apiClient.changeSubscription(p.id, interval),
    onSuccess: (data: any) => {
      setError(null);
      setNotice(`Switched to ${data.product_name} (${data.billing_interval}ly).`);
      invalidate();
    },
    onError: (err: any) => setError(err?.response?.data?.detail || 'Could not change plan'),
  });

  const cancelMutation = useMutation({
    mutationFn: (atEnd: boolean) => apiClient.cancelSubscription(atEnd),
    onSuccess: () => {
      setError(null);
      setNotice('Cancellation scheduled.');
      invalidate();
    },
    onError: (err: any) => setError(err?.response?.data?.detail || 'Could not cancel'),
  });

  function priceFor(p: Product): number {
    return interval === 'month' ? p.price_monthly_cents : p.price_yearly_cents;
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {currentSub && currentProduct && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <p className="text-sm text-gray-500">Current plan</p>
              <h2 className="text-2xl font-semibold text-gray-900">{currentSub.product_name}</h2>
              <p className="text-sm text-gray-600 mt-1">
                {money(currentSub.amount_cents, currentSub.currency)} / {currentSub.billing_interval} ·{' '}
                <span className="capitalize">{currentSub.status}</span>
              </p>
              {currentSub.current_period_end && (
                <p className="text-xs text-gray-500 mt-2 inline-flex items-center gap-1">
                  <CalendarClock className="w-3.5 h-3.5" />
                  Renews {formatDate(currentSub.current_period_end)}
                </p>
              )}
              {currentSub.cancel_at_period_end && (
                <p className="text-xs text-yellow-700 mt-2 font-medium">
                  Scheduled to cancel at period end.
                </p>
              )}
            </div>
            <div className="flex flex-col gap-2">
              {!currentSub.cancel_at_period_end && (
                <button
                  onClick={() => cancelMutation.mutate(true)}
                  disabled={cancelMutation.isPending}
                  className="px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-md hover:bg-red-50 disabled:opacity-60"
                >
                  Cancel at period end
                </button>
              )}
              <button
                onClick={() => cancelMutation.mutate(false)}
                disabled={cancelMutation.isPending}
                className="px-3 py-1.5 text-sm text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-60"
              >
                Cancel immediately
              </button>
            </div>
          </div>
        </div>
      )}

      {notice && (
        <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2 flex items-center justify-between">
          {notice}
          <button onClick={() => setNotice(null)}>
            <X className="w-4 h-4" />
          </button>
        </p>
      )}
      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2 flex items-center justify-between">
          {error}
          <button onClick={() => setError(null)}>
            <X className="w-4 h-4" />
          </button>
        </p>
      )}

      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Choose a plan</h3>
        <div className="inline-flex rounded-md border border-gray-200 p-0.5 bg-white">
          {(['month', 'year'] as const).map((v) => (
            <button
              key={v}
              onClick={() => setInterval(v)}
              className={cn(
                'px-3 py-1.5 text-sm rounded-md',
                interval === v ? 'bg-blue-600 text-white' : 'text-gray-700 hover:text-gray-900'
              )}
            >
              {v === 'month' ? 'Monthly' : 'Yearly'}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {products.map((p) => {
          const isCurrent =
            currentSub?.product_id === p.id && currentSub?.billing_interval === interval;
          const canSubscribe = !currentSub;
          const canSwitch = !!currentSub && !isCurrent;

          return (
            <div
              key={p.id}
              className={cn(
                'bg-white p-6 rounded-lg border flex flex-col',
                isCurrent ? 'border-blue-500 ring-1 ring-blue-500' : 'border-gray-200'
              )}
            >
              <div className="flex items-baseline justify-between mb-2">
                <h4 className="text-lg font-semibold text-gray-900">{p.name}</h4>
                {isCurrent && (
                  <span className="text-xs font-medium text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full">
                    Current
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-500 mb-4">{p.description}</p>
              <div className="mb-4 flex items-baseline gap-1">
                <CircleDollarSign className="w-5 h-5 text-gray-400" />
                <span className="text-3xl font-bold text-gray-900">
                  {money(priceFor(p), p.currency)}
                </span>
                <span className="text-sm text-gray-500">/{interval}</span>
              </div>
              <ul className="space-y-2 mb-6 flex-1">
                {(p.features || []).map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-gray-700">
                    <Check className="w-4 h-4 mt-0.5 text-green-600 shrink-0" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <button
                disabled={
                  isCurrent ||
                  subscribeMutation.isPending ||
                  changeMutation.isPending ||
                  (!canSubscribe && !canSwitch)
                }
                onClick={() =>
                  canSubscribe ? subscribeMutation.mutate(p) : changeMutation.mutate(p)
                }
                className={cn(
                  'w-full py-2 rounded-md text-sm font-medium',
                  isCurrent
                    ? 'bg-gray-100 text-gray-500 cursor-default'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                )}
              >
                {isCurrent
                  ? 'Current plan'
                  : canSubscribe
                  ? 'Subscribe'
                  : currentSub && priceFor(p) > (currentProduct ? priceFor(currentProduct) : 0)
                  ? 'Upgrade'
                  : 'Switch plan'}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

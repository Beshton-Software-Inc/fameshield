'use client';

import { FormEvent, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { apiClient } from '@/lib/api-client';

export default function ResetPasswordPage() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params?.get('token') || '';
  const type = params?.get('type') === 'staff' ? 'staff' : 'athlete';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tokenMissing, setTokenMissing] = useState(false);

  useEffect(() => {
    if (!token) setTokenMissing(true);
  }, [token]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords don't match");
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      if (type === 'staff') {
        await apiClient.staffResetPassword(token, password);
        router.replace('/admin');
      } else {
        await apiClient.athleteResetPassword(token, password);
        router.replace('/me');
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Reset failed');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="bg-white p-8 rounded-lg border border-gray-200 shadow-sm">
      <h1 className="text-2xl font-semibold text-gray-900 mb-1">Choose a new password</h1>
      <p className="text-sm text-gray-500 mb-6">
        {type === 'staff'
          ? 'For your staff / admin account.'
          : 'For your athlete account.'}
      </p>

      {tokenMissing ? (
        <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-3 space-y-2">
          <p>This reset link is missing its token. Try requesting a new one.</p>
          <p>
            <Link
              href={type === 'staff' ? '/admin/forgot' : '/forgot-password'}
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              Request a new reset link →
            </Link>
          </p>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">New password</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">At least 8 characters.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Confirm password</label>
            <input
              type="password"
              required
              minLength={8}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
          >
            {submitting ? 'Updating…' : 'Update password'}
          </button>
        </form>
      )}

      <p className="mt-6 text-sm text-gray-500 text-center">
        <Link
          href={type === 'staff' ? '/admin/login' : '/login'}
          className="text-blue-600 hover:text-blue-800 font-medium"
        >
          Back to sign in
        </Link>
      </p>
    </div>
  );
}

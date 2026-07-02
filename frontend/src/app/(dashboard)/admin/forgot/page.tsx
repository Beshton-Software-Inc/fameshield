'use client';

import { FormEvent, useState } from 'react';
import Link from 'next/link';
import { Shield } from 'lucide-react';
import { apiClient } from '@/lib/api-client';

export default function StaffForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await apiClient.staffForgotPassword(email);
      setSent(true);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Could not send reset email');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="h-16 bg-white border-b border-gray-200 flex items-center px-6">
        <Shield className="w-6 h-6 text-blue-600" />
        <span className="ml-2 text-lg font-bold text-gray-900">FameShield · Admin</span>
      </header>
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <div className="bg-white p-8 rounded-lg border border-gray-200 shadow-sm">
            <h1 className="text-2xl font-semibold text-gray-900 mb-1">
              Reset your staff password
            </h1>
            <p className="text-sm text-gray-500 mb-6">
              Enter your staff email. We'll send a reset link.
            </p>

            {sent ? (
              <div className="text-sm text-gray-700 bg-green-50 border border-green-200 rounded px-3 py-3 space-y-2">
                <p>
                  If a staff account exists for <strong>{email}</strong>, we've sent a reset
                  link. The link expires in 1 hour.
                </p>
                <p className="text-xs text-gray-500">
                  Not receiving anything? Check spam, or contact your system admin.
                </p>
              </div>
            ) : (
              <form onSubmit={onSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
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
                  {submitting ? 'Sending…' : 'Send reset link'}
                </button>
              </form>
            )}

            <p className="mt-6 text-sm text-gray-500 text-center">
              <Link href="/admin/login" className="text-blue-600 hover:text-blue-800 font-medium">
                Back to staff sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

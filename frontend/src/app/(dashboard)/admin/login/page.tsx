'use client';

import { FormEvent, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Shield } from 'lucide-react';
import { apiClient } from '@/lib/api-client';

export default function AdminLoginPage() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params?.get('next') || '/admin';

  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [form, setForm] = useState({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    organization_name: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (mode === 'register') {
        await apiClient.register({
          email: form.email,
          password: form.password,
          first_name: form.first_name,
          last_name: form.last_name,
          organization_name: form.organization_name,
        });
      }
      await apiClient.login(form.email, form.password);
      router.replace(next);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Login failed';
      setError(String(msg));
    } finally {
      setSubmitting(false);
    }
  }

  function update<K extends keyof typeof form>(k: K, v: (typeof form)[K]) {
    setForm((f) => ({ ...f, [k]: v }));
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
              {mode === 'login' ? 'Staff sign in' : 'Create staff account'}
            </h1>
            <p className="text-sm text-gray-500 mb-6">
              {mode === 'login'
                ? 'Admin dashboard access for staff and coaches.'
                : 'Register a new organization and its first admin.'}
            </p>

            <form onSubmit={onSubmit} className="space-y-4">
              {mode === 'register' && (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="First name" value={form.first_name} onChange={(v) => update('first_name', v)} required />
                    <Field label="Last name" value={form.last_name} onChange={(v) => update('last_name', v)} required />
                  </div>
                  <Field
                    label="Organization name"
                    value={form.organization_name}
                    onChange={(v) => update('organization_name', v)}
                    required
                  />
                </>
              )}
              <Field label="Email" type="email" value={form.email} onChange={(v) => update('email', v)} required />
              <Field
                label="Password"
                type="password"
                value={form.password}
                onChange={(v) => update('password', v)}
                required
                minLength={8}
              />
              {mode === 'login' && (
                <p className="text-right text-xs -mt-2">
                  <Link href="/admin/forgot" className="text-blue-600 hover:text-blue-800">
                    Forgot password?
                  </Link>
                </p>
              )}
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
                {submitting
                  ? mode === 'login'
                    ? 'Signing in…'
                    : 'Creating…'
                  : mode === 'login'
                  ? 'Sign in'
                  : 'Create account'}
              </button>
            </form>

            <p className="mt-6 text-sm text-gray-500 text-center">
              {mode === 'login' ? "Don't have a staff account yet?" : 'Already registered?'}{' '}
              <button
                type="button"
                onClick={() => {
                  setError(null);
                  setMode(mode === 'login' ? 'register' : 'login');
                }}
                className="text-blue-600 hover:text-blue-800 font-medium"
              >
                {mode === 'login' ? 'Create one' : 'Sign in'}
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = 'text',
  required,
  minLength,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
  minLength?: number;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        required={required}
        minLength={minLength}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  );
}

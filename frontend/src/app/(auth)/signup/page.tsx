'use client';

import { FormEvent, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';

export default function SignupPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    date_of_birth: '',
    sport: '',
    phone: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await apiClient.athleteRegister({
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
        password: form.password,
        date_of_birth: form.date_of_birth,
        sport: form.sport,
        phone: form.phone || undefined,
      });
      router.push('/me');
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Signup failed';
      setError(String(msg));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="bg-white p-8 rounded-lg border border-gray-200 shadow-sm">
      <h1 className="text-2xl font-semibold text-gray-900 mb-1">Create an athlete account</h1>
      <p className="text-sm text-gray-500 mb-6">
        Personal dashboard, subscription, and monitoring of your online appearances.
      </p>

      <form onSubmit={onSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <FormField label="First name" value={form.first_name} onChange={(v) => update('first_name', v)} required />
          <FormField label="Last name" value={form.last_name} onChange={(v) => update('last_name', v)} required />
        </div>
        <FormField label="Email" type="email" value={form.email} onChange={(v) => update('email', v)} required />
        <FormField
          label="Password"
          type="password"
          value={form.password}
          onChange={(v) => update('password', v)}
          required
          minLength={8}
          help="At least 8 characters."
        />
        <div className="grid grid-cols-2 gap-3">
          <FormField
            label="Date of birth"
            type="date"
            value={form.date_of_birth}
            onChange={(v) => update('date_of_birth', v)}
            required
          />
          <FormField label="Sport" value={form.sport} onChange={(v) => update('sport', v)} required />
        </div>
        <FormField label="Phone (optional)" value={form.phone} onChange={(v) => update('phone', v)} />

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
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <p className="mt-6 text-sm text-gray-500 text-center">
        Already have an account?{' '}
        <Link href="/login" className="text-blue-600 hover:text-blue-800 font-medium">
          Sign in
        </Link>
      </p>
    </div>
  );
}

function FormField({
  label,
  value,
  onChange,
  type = 'text',
  required,
  minLength,
  help,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
  minLength?: number;
  help?: string;
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
      {help && <p className="mt-1 text-xs text-gray-500">{help}</p>}
    </div>
  );
}

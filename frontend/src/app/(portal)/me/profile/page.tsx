'use client';

import { FormEvent, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

type ProfileForm = {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  sport: string;
  bio: string;
  profile_image_url: string;
  date_of_birth: string;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
};

const EMPTY: ProfileForm = {
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  sport: '',
  bio: '',
  profile_image_url: '',
  date_of_birth: '',
  address_line1: '',
  address_line2: '',
  city: '',
  state: '',
  postal_code: '',
  country: '',
};

export default function ProfilePage() {
  const qc = useQueryClient();
  const meQuery = useQuery({ queryKey: ['me'], queryFn: () => apiClient.getMe() });
  const [form, setForm] = useState<ProfileForm>(EMPTY);
  const [status, setStatus] = useState<null | 'saved' | 'error'>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (meQuery.data) {
      const d = meQuery.data;
      setForm({
        first_name: d.first_name || '',
        last_name: d.last_name || '',
        email: d.email || '',
        phone: d.phone || '',
        sport: d.sport || '',
        bio: d.bio || '',
        profile_image_url: d.profile_image_url || '',
        date_of_birth: d.date_of_birth || '',
        address_line1: d.address_line1 || '',
        address_line2: d.address_line2 || '',
        city: d.city || '',
        state: d.state || '',
        postal_code: d.postal_code || '',
        country: d.country || '',
      });
    }
  }, [meQuery.data]);

  const mutation = useMutation({
    mutationFn: (payload: Partial<ProfileForm>) => apiClient.updateMyProfile(payload),
    onSuccess: () => {
      setStatus('saved');
      setErrorMsg(null);
      qc.invalidateQueries({ queryKey: ['me'] });
    },
    onError: (err: any) => {
      setStatus('error');
      setErrorMsg(err?.response?.data?.detail || err?.message || 'Update failed');
    },
  });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setStatus(null);
    const payload: Partial<ProfileForm> = {};
    (Object.keys(form) as (keyof ProfileForm)[]).forEach((k) => {
      payload[k] = form[k] === '' ? undefined : (form[k] as any);
    });
    mutation.mutate(payload);
  }

  function update<K extends keyof ProfileForm>(k: K, v: ProfileForm[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  if (meQuery.isLoading) {
    return <p className="text-sm text-gray-500">Loading profile…</p>;
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6 max-w-3xl">
      <Section title="Personal information">
        <div className="grid grid-cols-2 gap-3">
          <Field label="First name" value={form.first_name} onChange={(v) => update('first_name', v)} required />
          <Field label="Last name" value={form.last_name} onChange={(v) => update('last_name', v)} required />
        </div>
        <Field label="Email" type="email" value={form.email} onChange={(v) => update('email', v)} required />
        <div className="grid grid-cols-2 gap-3">
          <Field label="Phone" value={form.phone} onChange={(v) => update('phone', v)} />
          <Field label="Date of birth" type="date" value={form.date_of_birth} onChange={(v) => update('date_of_birth', v)} />
        </div>
        <Field label="Sport" value={form.sport} onChange={(v) => update('sport', v)} required />
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Bio</label>
          <textarea
            value={form.bio}
            onChange={(e) => update('bio', e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <Field
          label="Profile image URL"
          value={form.profile_image_url}
          onChange={(v) => update('profile_image_url', v)}
        />
      </Section>

      <Section title="Address">
        <Field label="Line 1" value={form.address_line1} onChange={(v) => update('address_line1', v)} />
        <Field label="Line 2" value={form.address_line2} onChange={(v) => update('address_line2', v)} />
        <div className="grid grid-cols-2 gap-3">
          <Field label="City" value={form.city} onChange={(v) => update('city', v)} />
          <Field label="State / Region" value={form.state} onChange={(v) => update('state', v)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Postal code" value={form.postal_code} onChange={(v) => update('postal_code', v)} />
          <Field label="Country (2-letter)" value={form.country} onChange={(v) => update('country', v.toUpperCase())} />
        </div>
      </Section>

      {status === 'saved' && (
        <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2">
          Saved.
        </p>
      )}
      {status === 'error' && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {errorMsg || 'Update failed.'}
        </p>
      )}

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={mutation.isPending}
          className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
        >
          {mutation.isPending ? 'Saving…' : 'Save changes'}
        </button>
      </div>
    </form>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white p-6 rounded-lg border border-gray-200 space-y-4">
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      {children}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = 'text',
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        required={required}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  );
}

import { ReactNode } from 'react';
import Link from 'next/link';
import { Shield } from 'lucide-react';

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="h-16 bg-white border-b border-gray-200 flex items-center px-6">
        <Link href="/" className="flex items-center">
          <Shield className="w-6 h-6 text-blue-600" />
          <span className="ml-2 text-lg font-bold text-gray-900">FameShield</span>
        </Link>
      </header>
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">{children}</div>
      </div>
    </div>
  );
}

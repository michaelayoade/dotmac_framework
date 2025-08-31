"use client";

import { MarketingResourceCenter } from '@/components/marketing/MarketingResourceCenter';

export default function MarketingPage() {
  return (
    <div className="container mx-auto px-4 py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Marketing Resource Center</h1>
        <p className="text-gray-600 mt-1">
          Access marketing materials, co-marketing opportunities, and brand resources
        </p>
      </div>
      
      <MarketingResourceCenter />
    </div>
  );
}
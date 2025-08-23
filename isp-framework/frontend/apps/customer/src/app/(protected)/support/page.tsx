import { Suspense } from 'react';
import { CustomerLayout } from '../../../components/layout/CustomerLayout';
import { SupportTickets } from '../../../components/support/SupportTickets';
import { LiveChatWidget } from '../../../components/support/LiveChatWidget';
import { KnowledgeBase } from '../../../components/support/KnowledgeBase';
import { SupportCenter } from '../../../components/support/SupportCenter';
import { SkeletonCard } from '@dotmac/primitives';

export default function SupportPage() {
  return (
    <CustomerLayout>
      <div className='space-y-6'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Support Center</h1>
          <p className='mt-1 text-sm text-gray-500'>
            Get help with your services, manage support tickets, and find answers
          </p>
        </div>

        <Suspense fallback={<SupportSkeleton />}>
          <SupportContent />
        </Suspense>

        {/* Live Chat Widget */}
        <LiveChatWidget />
      </div>
    </CustomerLayout>
  );
}

function SupportContent() {
  return (
    <div className='space-y-8'>
      <SupportCenter />
      <div className='grid grid-cols-1 lg:grid-cols-3 gap-8'>
        <div className='lg:col-span-2'>
          <SupportTickets />
        </div>
        <div>
          <KnowledgeBase />
        </div>
      </div>
    </div>
  );
}

function SupportSkeleton() {
  return (
    <div className='space-y-6'>
      <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
      <div className='grid grid-cols-1 lg:grid-cols-3 gap-6'>
        <div className='lg:col-span-2'>
          <SkeletonCard className='h-96' />
        </div>
        <div>
          <SkeletonCard className='h-96' />
        </div>
      </div>
    </div>
  );
}

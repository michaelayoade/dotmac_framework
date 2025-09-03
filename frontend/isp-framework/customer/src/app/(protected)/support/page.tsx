// import { SkeletonCard } from '@dotmac/primitives';

// Temporary skeleton component
const SkeletonCard = ({ className = 'h-32' }: { className?: string }) => (
  <div className={`bg-gray-200 rounded animate-pulse ${className}`} />
);
import { Suspense } from 'react';
import { CustomerLayout } from '../../../components/layout/CustomerLayout';
import { KnowledgeBase } from '../../../components/support/KnowledgeBase';
import { LiveChatWidget } from '../../../components/support/LiveChatWidget';
import { SupportCenter } from '../../../components/support/SupportCenter';
import { SupportTickets } from '../../../components/support/SupportTickets';

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

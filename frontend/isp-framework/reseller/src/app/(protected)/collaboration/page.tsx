'use client';

import { PartnerCollaborationHub } from '@/components/collaboration/PartnerCollaborationHub';

export default function CollaborationPage() {
  return (
    <div className='container mx-auto px-4 py-6'>
      <div className='mb-6'>
        <h1 className='text-2xl font-bold text-gray-900'>Partner Collaboration</h1>
        <p className='text-gray-600 mt-1'>
          Collaborate with DotMac and other partners on projects, deals, and initiatives
        </p>
      </div>

      <PartnerCollaborationHub />
    </div>
  );
}

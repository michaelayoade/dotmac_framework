/**
 * Incident Response Page
 * Security incident management and response workflows
 */

import { IncidentResponseWorkflow } from '@/components/security/IncidentResponseWorkflow';

export const metadata = {
  title: 'Incident Response - Management Admin',
  description: 'Security incident management and response workflows',
};

export default function IncidentResponsePage() {
  return (
    <div className='space-y-6'>
      <IncidentResponseWorkflow />
    </div>
  );
}

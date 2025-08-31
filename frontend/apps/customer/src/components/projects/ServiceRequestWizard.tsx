"use client";
import React from 'react';
import { WorkflowTemplate } from '@dotmac/patterns/templates';
import type { WorkflowConfig } from '@dotmac/patterns/templates';
import { Card } from '@dotmac/primitives';

const config: WorkflowConfig = {
  type: 'workflow',
  title: 'New Service Request',
  portal: 'customer',
  steps: [
    {
      id: 'type',
      title: 'Request Type',
      type: 'form',
      required: true,
      fields: [
        { key: 'requestType', label: 'Type', type: 'select', required: true, options: [
          { value: 'installation', label: 'Installation' },
          { value: 'upgrade', label: 'Upgrade' },
          { value: 'relocation', label: 'Relocation' },
        ]}
      ]
    },
    {
      id: 'details',
      title: 'Details',
      type: 'form',
      required: true,
      fields: [
        { key: 'location', label: 'Location', type: 'text', required: true },
        { key: 'desiredDate', label: 'Desired Date', type: 'date', required: true },
        { key: 'notes', label: 'Notes', type: 'textarea' }
      ]
    },
    {
      id: 'attachments',
      title: 'Attachments',
      type: 'form',
      required: false,
      fields: [
        { key: 'attachments', label: 'Files', type: 'file' }
      ]
    },
    {
      id: 'review',
      title: 'Review & Submit',
      type: 'review',
      required: true,
      fields: []
    }
  ],
  allowStepNavigation: true,
  showProgress: true,
  showStepNumbers: true,
  persistData: true,
  autoSave: true,
  autoSaveInterval: 15000,
};

export function ServiceRequestWizard() {
  async function onComplete(data: Record<string, any>) {
    await fetch('/api/customer/projects', { method: 'POST', body: JSON.stringify(data) });
  }

  return (
    <Card className="p-4 mt-6" data-testid="service-request-wizard">
      <WorkflowTemplate config={config} onComplete={onComplete} />
    </Card>
  );
}


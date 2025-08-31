'use client';

import React, { useState } from 'react';
import { WorkflowTemplate, WorkflowStepProps } from '@dotmac/primitives/templates/WorkflowTemplate';
import { CameraIcon, DocumentTextIcon, SignatureIcon, CheckCircleIcon } from '@heroicons/react/24/outline';

interface InstallationData {
  siteInfo: {
    address: string;
    customerName: string;
    contactNumber: string;
    equipmentLocation: string;
    accessNotes: string;
  };
  equipment: {
    modemModel: string;
    modemSerial: string;
    routerModel: string;
    routerSerial: string;
    cableLength: number;
    additionalEquipment: string[];
  };
  testing: {
    signalStrength: number;
    downloadSpeed: number;
    uploadSpeed: number;
    ping: number;
    testResults: 'passed' | 'failed' | 'pending';
    issues: string[];
  };
  photos: {
    beforeInstall: File[];
    duringInstall: File[];
    afterInstall: File[];
    equipmentPhotos: File[];
  };
  completion: {
    customerSignature: string;
    technicianNotes: string;
    completionTime: Date;
    followUpRequired: boolean;
    followUpNotes: string;
  };
}

// Step 1: Site Information
const SiteInfoStep: React.FC<WorkflowStepProps> = ({ data, onChange }) => {
  const [siteInfo, setSiteInfo] = useState(data.siteInfo || {
    address: '',
    customerName: '',
    contactNumber: '',
    equipmentLocation: '',
    accessNotes: ''
  });

  const handleChange = (field: string, value: string) => {
    const updated = { ...siteInfo, [field]: value };
    setSiteInfo(updated);
    onChange({ ...data, siteInfo: updated });
  };

  return (
    <div className="space-y-6" role="form" aria-labelledby="site-info-heading">
      <h3 id="site-info-heading" className="sr-only">Site Information</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label htmlFor="address" className="block text-sm font-medium text-gray-700 mb-2">
            Installation Address *
          </label>
          <input
            id="address"
            type="text"
            value={siteInfo.address}
            onChange={(e) => handleChange('address', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
            aria-required="true"
          />
        </div>

        <div>
          <label htmlFor="customerName" className="block text-sm font-medium text-gray-700 mb-2">
            Customer Name *
          </label>
          <input
            id="customerName"
            type="text"
            value={siteInfo.customerName}
            onChange={(e) => handleChange('customerName', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
            aria-required="true"
          />
        </div>

        <div>
          <label htmlFor="contactNumber" className="block text-sm font-medium text-gray-700 mb-2">
            Contact Number
          </label>
          <input
            id="contactNumber"
            type="tel"
            value={siteInfo.contactNumber}
            onChange={(e) => handleChange('contactNumber', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label htmlFor="equipmentLocation" className="block text-sm font-medium text-gray-700 mb-2">
            Equipment Location *
          </label>
          <select
            id="equipmentLocation"
            value={siteInfo.equipmentLocation}
            onChange={(e) => handleChange('equipmentLocation', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
            aria-required="true"
          >
            <option value="">Select location...</option>
            <option value="basement">Basement</option>
            <option value="garage">Garage</option>
            <option value="utility-room">Utility Room</option>
            <option value="living-room">Living Room</option>
            <option value="office">Home Office</option>
            <option value="other">Other</option>
          </select>
        </div>
      </div>

      <div>
        <label htmlFor="accessNotes" className="block text-sm font-medium text-gray-700 mb-2">
          Access Notes / Special Instructions
        </label>
        <textarea
          id="accessNotes"
          value={siteInfo.accessNotes}
          onChange={(e) => handleChange('accessNotes', e.target.value)}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Gate codes, special access instructions, pet information, etc."
        />
      </div>
    </div>
  );
};

// Step 2: Equipment Installation
const EquipmentStep: React.FC<WorkflowStepProps> = ({ data, onChange }) => {
  const [equipment, setEquipment] = useState(data.equipment || {
    modemModel: '',
    modemSerial: '',
    routerModel: '',
    routerSerial: '',
    cableLength: 0,
    additionalEquipment: []
  });

  const handleChange = (field: string, value: any) => {
    const updated = { ...equipment, [field]: value };
    setEquipment(updated);
    onChange({ ...data, equipment: updated });
  };

  const addEquipment = () => {
    const newEquipment = prompt('Add additional equipment:');
    if (newEquipment) {
      handleChange('additionalEquipment', [...equipment.additionalEquipment, newEquipment]);
    }
  };

  return (
    <div className="space-y-6" role="form" aria-labelledby="equipment-heading">
      <h3 id="equipment-heading" className="sr-only">Equipment Installation</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label htmlFor="modemModel" className="block text-sm font-medium text-gray-700 mb-2">
            Modem Model *
          </label>
          <select
            id="modemModel"
            value={equipment.modemModel}
            onChange={(e) => handleChange('modemModel', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
            aria-required="true"
          >
            <option value="">Select modem...</option>
            <option value="ARRIS-SB8200">ARRIS SURFboard SB8200</option>
            <option value="NETGEAR-CM1000">NETGEAR Nighthawk CM1000</option>
            <option value="MOTOROLA-MB8600">Motorola MB8600</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div>
          <label htmlFor="modemSerial" className="block text-sm font-medium text-gray-700 mb-2">
            Modem Serial Number *
          </label>
          <input
            id="modemSerial"
            type="text"
            value={equipment.modemSerial}
            onChange={(e) => handleChange('modemSerial', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
            aria-required="true"
          />
        </div>

        <div>
          <label htmlFor="routerModel" className="block text-sm font-medium text-gray-700 mb-2">
            Router Model
          </label>
          <select
            id="routerModel"
            value={equipment.routerModel}
            onChange={(e) => handleChange('routerModel', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">No router installed</option>
            <option value="ASUS-AX6000">ASUS AX6000</option>
            <option value="NETGEAR-AX12">NETGEAR Nighthawk AX12</option>
            <option value="LINKSYS-MX4200">Linksys Velop MX4200</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div>
          <label htmlFor="routerSerial" className="block text-sm font-medium text-gray-700 mb-2">
            Router Serial Number
          </label>
          <input
            id="routerSerial"
            type="text"
            value={equipment.routerSerial}
            onChange={(e) => handleChange('routerSerial', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label htmlFor="cableLength" className="block text-sm font-medium text-gray-700 mb-2">
            Cable Length (feet) *
          </label>
          <input
            id="cableLength"
            type="number"
            value={equipment.cableLength}
            onChange={(e) => handleChange('cableLength', parseInt(e.target.value) || 0)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            min="0"
            required
            aria-required="true"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Additional Equipment
        </label>
        <div className="space-y-2">
          {equipment.additionalEquipment.map((item, index) => (
            <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
              <span>{item}</span>
              <button
                onClick={() => {
                  const filtered = equipment.additionalEquipment.filter((_, i) => i !== index);
                  handleChange('additionalEquipment', filtered);
                }}
                className="text-red-600 hover:text-red-800"
                aria-label={`Remove ${item}`}
              >
                Remove
              </button>
            </div>
          ))}
          <button
            onClick={addEquipment}
            className="text-blue-600 hover:text-blue-800 text-sm"
          >
            + Add Equipment
          </button>
        </div>
      </div>
    </div>
  );
};

// Step 3: Connection Testing
const TestingStep: React.FC<WorkflowStepProps> = ({ data, onChange }) => {
  const [testing, setTesting] = useState(data.testing || {
    signalStrength: 0,
    downloadSpeed: 0,
    uploadSpeed: 0,
    ping: 0,
    testResults: 'pending',
    issues: []
  });

  const handleChange = (field: string, value: any) => {
    const updated = { ...testing, [field]: value };
    setTesting(updated);
    onChange({ ...data, testing: updated });
  };

  const runSpeedTest = () => {
    // Simulate speed test
    setTesting(prev => ({ ...prev, testResults: 'pending' }));
    setTimeout(() => {
      const results = {
        signalStrength: Math.floor(Math.random() * 20) - 10,
        downloadSpeed: Math.floor(Math.random() * 900) + 100,
        uploadSpeed: Math.floor(Math.random() * 100) + 50,
        ping: Math.floor(Math.random() * 20) + 5,
        testResults: 'passed' as const
      };
      const updated = { ...testing, ...results };
      setTesting(updated);
      onChange({ ...data, testing: updated });
    }, 3000);
  };

  return (
    <div className="space-y-6" role="form" aria-labelledby="testing-heading">
      <h3 id="testing-heading" className="sr-only">Connection Testing</h3>
      
      <div className="text-center">
        <button
          onClick={runSpeedTest}
          disabled={testing.testResults === 'pending'}
          className="
            px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700
            disabled:opacity-50 disabled:cursor-not-allowed
            focus:outline-none focus:ring-2 focus:ring-blue-500
          "
        >
          {testing.testResults === 'pending' ? 'Testing...' : 'Run Speed Test'}
        </button>
      </div>

      {testing.testResults !== 'pending' && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg border text-center">
            <div className="text-2xl font-bold text-gray-900">{testing.signalStrength}</div>
            <div className="text-sm text-gray-600">Signal (dBm)</div>
          </div>
          <div className="bg-white p-4 rounded-lg border text-center">
            <div className="text-2xl font-bold text-gray-900">{testing.downloadSpeed}</div>
            <div className="text-sm text-gray-600">Download (Mbps)</div>
          </div>
          <div className="bg-white p-4 rounded-lg border text-center">
            <div className="text-2xl font-bold text-gray-900">{testing.uploadSpeed}</div>
            <div className="text-sm text-gray-600">Upload (Mbps)</div>
          </div>
          <div className="bg-white p-4 rounded-lg border text-center">
            <div className="text-2xl font-bold text-gray-900">{testing.ping}</div>
            <div className="text-sm text-gray-600">Ping (ms)</div>
          </div>
        </div>
      )}
    </div>
  );
};

// Step 4: Photo Documentation
const PhotoStep: React.FC<WorkflowStepProps> = ({ data, onChange }) => {
  const [photos, setPhotos] = useState(data.photos || {
    beforeInstall: [],
    duringInstall: [],
    afterInstall: [],
    equipmentPhotos: []
  });

  const handlePhotoUpload = (category: keyof typeof photos, files: FileList) => {
    const newFiles = Array.from(files);
    const updated = { ...photos, [category]: [...photos[category], ...newFiles] };
    setPhotos(updated);
    onChange({ ...data, photos: updated });
  };

  return (
    <div className="space-y-6" role="form" aria-labelledby="photos-heading">
      <h3 id="photos-heading" className="sr-only">Photo Documentation</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {[
          { key: 'beforeInstall', label: 'Before Installation' },
          { key: 'duringInstall', label: 'During Installation' },
          { key: 'afterInstall', label: 'After Installation' },
          { key: 'equipmentPhotos', label: 'Equipment Photos' }
        ].map(({ key, label }) => (
          <div key={key} className="border-2 border-dashed border-gray-300 rounded-lg p-6">
            <div className="text-center">
              <CameraIcon className="mx-auto h-12 w-12 text-gray-400" />
              <div className="mt-4">
                <label htmlFor={`${key}-upload`} className="cursor-pointer">
                  <span className="mt-2 block text-sm font-medium text-gray-900">
                    {label}
                  </span>
                  <input
                    id={`${key}-upload`}
                    type="file"
                    multiple
                    accept="image/*"
                    className="sr-only"
                    onChange={(e) => e.target.files && handlePhotoUpload(key as keyof typeof photos, e.target.files)}
                  />
                  <span className="mt-1 block text-sm text-gray-600">
                    Click to upload photos
                  </span>
                </label>
              </div>
              <div className="mt-2">
                <span className="text-sm text-gray-500">
                  {photos[key as keyof typeof photos].length} photos uploaded
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Step 5: Completion and Signature
const CompletionStep: React.FC<WorkflowStepProps> = ({ data, onChange }) => {
  const [completion, setCompletion] = useState(data.completion || {
    customerSignature: '',
    technicianNotes: '',
    completionTime: new Date(),
    followUpRequired: false,
    followUpNotes: ''
  });

  const handleChange = (field: string, value: any) => {
    const updated = { ...completion, [field]: value };
    setCompletion(updated);
    onChange({ ...data, completion: updated });
  };

  return (
    <div className="space-y-6" role="form" aria-labelledby="completion-heading">
      <h3 id="completion-heading" className="sr-only">Installation Completion</h3>
      
      <div>
        <label htmlFor="technicianNotes" className="block text-sm font-medium text-gray-700 mb-2">
          Technician Notes
        </label>
        <textarea
          id="technicianNotes"
          value={completion.technicianNotes}
          onChange={(e) => handleChange('technicianNotes', e.target.value)}
          rows={4}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Installation notes, issues encountered, recommendations..."
        />
      </div>

      <div className="flex items-center">
        <input
          id="followUpRequired"
          type="checkbox"
          checked={completion.followUpRequired}
          onChange={(e) => handleChange('followUpRequired', e.target.checked)}
          className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
        />
        <label htmlFor="followUpRequired" className="ml-2 text-sm text-gray-700">
          Follow-up visit required
        </label>
      </div>

      {completion.followUpRequired && (
        <div>
          <label htmlFor="followUpNotes" className="block text-sm font-medium text-gray-700 mb-2">
            Follow-up Notes
          </label>
          <textarea
            id="followUpNotes"
            value={completion.followUpNotes}
            onChange={(e) => handleChange('followUpNotes', e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Reason for follow-up, scheduled date, specific issues..."
          />
        </div>
      )}

      <div className="border-2 border-dashed border-gray-300 rounded-lg p-6">
        <div className="text-center">
          <SignatureIcon className="mx-auto h-12 w-12 text-gray-400" />
          <div className="mt-4">
            <h4 className="text-lg font-medium text-gray-900">Customer Signature</h4>
            <p className="text-sm text-gray-600 mt-2">
              Customer signature required to complete installation
            </p>
            <div className="mt-4">
              {/* Signature pad placeholder */}
              <div className="w-full h-32 bg-gray-50 border-2 border-gray-200 rounded flex items-center justify-center">
                <span className="text-gray-400">Signature Pad Placeholder</span>
              </div>
              <button
                className="mt-2 text-sm text-blue-600 hover:text-blue-800"
                onClick={() => handleChange('customerSignature', 'signature-placeholder')}
              >
                Clear Signature
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export const InstallationWorkflow: React.FC = () => {
  const steps = [
    {
      id: 'site-info',
      title: 'Site Information',
      description: 'Collect installation site details and customer information',
      component: SiteInfoStep,
      validation: async () => {
        // Add validation logic
        return true;
      },
      required: true
    },
    {
      id: 'equipment',
      title: 'Equipment Installation',
      description: 'Document installed equipment and hardware',
      component: EquipmentStep,
      validation: async () => true,
      required: true
    },
    {
      id: 'testing',
      title: 'Connection Testing',
      description: 'Test connection speeds and signal quality',
      component: TestingStep,
      validation: async () => true,
      required: true
    },
    {
      id: 'photos',
      title: 'Photo Documentation',
      description: 'Take photos for installation documentation',
      component: PhotoStep,
      validation: async () => true
    },
    {
      id: 'completion',
      title: 'Completion & Signature',
      description: 'Get customer signature and finalize installation',
      component: CompletionStep,
      validation: async () => true,
      required: true
    }
  ];

  const handleComplete = (data: InstallationData) => {
    // Submit to API
    // await installationAPI.submit(data);
    
    // Navigate to success page or dashboard
    // router.push('/dashboard');
  };

  const handleCancel = () => {
    // Handle cancellation
    if (confirm('Are you sure you want to cancel this installation?')) {
      // Navigate back or clear data
    }
  };

  return (
    <WorkflowTemplate
      title="Equipment Installation"
      subtitle="Complete all steps to finish the installation"
      steps={steps}
      onComplete={handleComplete}
      onCancel={handleCancel}
      showProgress={true}
      className="min-h-screen flex flex-col"
    />
  );
};
/**
 * Family Management Component
 * Manages family members and parental controls
 */

'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@dotmac/primitives';

interface FamilyMember {
  id: string;
  name: string;
  email: string;
  role: 'primary' | 'secondary' | 'child';
  permissions: string[];
  deviceLimit: number;
  currentDevices: number;
}

export function FamilyManagement() {
  const [familyMembers, setFamilyMembers] = useState<FamilyMember[]>([
    {
      id: '1',
      name: 'John Doe',
      email: 'john@example.com',
      role: 'primary',
      permissions: ['billing', 'support', 'settings'],
      deviceLimit: 10,
      currentDevices: 5,
    },
    {
      id: '2',
      name: 'Jane Doe',
      email: 'jane@example.com',
      role: 'secondary',
      permissions: ['support'],
      deviceLimit: 5,
      currentDevices: 3,
    },
  ]);

  const [showAddMember, setShowAddMember] = useState(false);
  const [newMember, setNewMember] = useState({
    name: '',
    email: '',
    role: 'secondary' as const,
    deviceLimit: 3,
  });

  const addFamilyMember = () => {
    if (newMember.name && newMember.email) {
      const member: FamilyMember = {
        id: Date.now().toString(),
        ...newMember,
        permissions:
          newMember.role === 'primary' ? ['billing', 'support', 'settings'] : ['support'],
        currentDevices: 0,
      };
      setFamilyMembers([...familyMembers, member]);
      setNewMember({ name: '', email: '', role: 'secondary', deviceLimit: 3 });
      setShowAddMember(false);
    }
  };

  const removeFamilyMember = (id: string) => {
    setFamilyMembers(familyMembers.filter((member) => member.id !== id));
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'primary':
        return 'bg-blue-100 text-blue-800';
      case 'secondary':
        return 'bg-green-100 text-green-800';
      case 'child':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <Card>
      <div className='p-6'>
        <div className='flex items-center justify-between mb-4'>
          <h2 className='text-lg font-semibold text-gray-900'>Family & Device Management</h2>
          <Button size='sm' onClick={() => setShowAddMember(!showAddMember)}>
            {showAddMember ? 'Cancel' : 'Add Member'}
          </Button>
        </div>

        {/* Add New Member Form */}
        {showAddMember && (
          <div className='mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg'>
            <h3 className='text-sm font-medium text-gray-900 mb-3'>Add Family Member</h3>
            <div className='space-y-3'>
              <div>
                <Input
                  placeholder='Full Name'
                  value={newMember.name}
                  onChange={(e) => setNewMember({ ...newMember, name: e.target.value })}
                />
              </div>
              <div>
                <Input
                  type='email'
                  placeholder='Email Address'
                  value={newMember.email}
                  onChange={(e) => setNewMember({ ...newMember, email: e.target.value })}
                />
              </div>
              <div className='grid grid-cols-2 gap-3'>
                <div>
                  <select
                    value={newMember.role}
                    onChange={(e) => setNewMember({ ...newMember, role: e.target.value as any })}
                    className='w-full px-3 py-2 border border-gray-300 rounded-md text-sm'
                  >
                    <option value='secondary'>Secondary User</option>
                    <option value='child'>Child</option>
                  </select>
                </div>
                <div>
                  <Input
                    type='number'
                    min='1'
                    max='10'
                    placeholder='Device Limit'
                    value={newMember.deviceLimit.toString()}
                    onChange={(e) =>
                      setNewMember({ ...newMember, deviceLimit: parseInt(e.target.value) || 3 })
                    }
                  />
                </div>
              </div>
              <div className='flex space-x-2'>
                <Button size='sm' onClick={addFamilyMember}>
                  Add Member
                </Button>
                <Button size='sm' variant='outline' onClick={() => setShowAddMember(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Family Members List */}
        <div className='space-y-4'>
          {familyMembers.map((member) => (
            <div key={member.id} className='border border-gray-200 rounded-lg p-4'>
              <div className='flex items-center justify-between'>
                <div className='flex-1'>
                  <div className='flex items-center space-x-3 mb-2'>
                    <h3 className='font-medium text-gray-900'>{member.name}</h3>
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full ${getRoleColor(member.role)}`}
                    >
                      {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                    </span>
                  </div>
                  <p className='text-sm text-gray-600 mb-2'>{member.email}</p>

                  {/* Device Usage */}
                  <div className='flex items-center space-x-4 text-sm'>
                    <span className='text-gray-600'>
                      Devices: {member.currentDevices}/{member.deviceLimit}
                    </span>
                    <div className='flex-1 bg-gray-200 rounded-full h-2 max-w-32'>
                      <div
                        className='bg-blue-500 h-2 rounded-full'
                        style={{
                          width: `${Math.min((member.currentDevices / member.deviceLimit) * 100, 100)}%`,
                        }}
                      />
                    </div>
                  </div>

                  {/* Permissions */}
                  <div className='mt-2'>
                    <div className='flex flex-wrap gap-1'>
                      {member.permissions.map((permission) => (
                        <span
                          key={permission}
                          className='px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded'
                        >
                          {permission}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {member.role !== 'primary' && (
                  <div className='ml-4 flex flex-col space-y-2'>
                    <Button size='sm' variant='outline'>
                      Edit
                    </Button>
                    <Button
                      size='sm'
                      variant='outline'
                      onClick={() => removeFamilyMember(member.id)}
                      className='text-red-600 hover:text-red-700 border-red-300 hover:border-red-400'
                    >
                      Remove
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Parental Controls Info */}
        <div className='mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg'>
          <div className='flex items-start'>
            <svg className='h-5 w-5 text-blue-400 mt-0.5' fill='currentColor' viewBox='0 0 20 20'>
              <path
                fillRule='evenodd'
                d='M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z'
                clipRule='evenodd'
              />
            </svg>
            <div className='ml-3'>
              <h3 className='text-sm font-medium text-blue-800'>Parental Controls Available</h3>
              <div className='mt-1 text-sm text-blue-700'>
                Manage content filtering, time restrictions, and device access for child accounts.
              </div>
              <Button
                size='sm'
                variant='outline'
                className='mt-2 border-blue-300 text-blue-700 hover:bg-blue-100'
              >
                Configure Controls
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

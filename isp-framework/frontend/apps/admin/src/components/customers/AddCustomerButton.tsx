'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createCustomerAction } from '../../app/actions/customers';

export function AddCustomerButton() {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);

    const formData = new FormData(e.currentTarget);
    const result = await createCustomerAction(formData);

    setLoading(false);

    if (result.success) {
      setIsOpen(false);
      router.refresh();
    } else {
      alert(result.error || 'Failed to create customer');
    }
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className='rounded-lg bg-primary px-4 py-2 text-white transition-colors hover:bg-primary/90'
      >
        Add Customer
      </button>

      {isOpen && (
        <div className='fixed inset-0 z-50 overflow-y-auto'>
          <div className='flex min-h-screen items-center justify-center p-4'>
            <div className='fixed inset-0 bg-black/50' onClick={() => setIsOpen(false)} />

            <div className='relative bg-white rounded-lg shadow-xl max-w-md w-full p-6'>
              <h2 className='text-xl font-bold mb-4'>Add New Customer</h2>

              <form onSubmit={handleSubmit} className='space-y-4'>
                <div>
                  <label htmlFor='name' className='block text-sm font-medium text-gray-700'>
                    Name
                  </label>
                  <input
                    type='text'
                    name='name'
                    id='name'
                    required
                    className='mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
                  />
                </div>

                <div>
                  <label htmlFor='email' className='block text-sm font-medium text-gray-700'>
                    Email
                  </label>
                  <input
                    type='email'
                    name='email'
                    id='email'
                    required
                    className='mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
                  />
                </div>

                <div>
                  <label htmlFor='phone' className='block text-sm font-medium text-gray-700'>
                    Phone
                  </label>
                  <input
                    type='tel'
                    name='phone'
                    id='phone'
                    required
                    className='mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
                  />
                </div>

                <div>
                  <label htmlFor='address' className='block text-sm font-medium text-gray-700'>
                    Address
                  </label>
                  <textarea
                    name='address'
                    id='address'
                    rows={2}
                    required
                    className='mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
                  />
                </div>

                <div>
                  <label htmlFor='plan' className='block text-sm font-medium text-gray-700'>
                    Plan
                  </label>
                  <select
                    name='plan'
                    id='plan'
                    required
                    className='mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
                  >
                    <option value='basic'>Basic (50 Mbps)</option>
                    <option value='standard'>Standard (100 Mbps)</option>
                    <option value='premium'>Premium (500 Mbps)</option>
                    <option value='enterprise'>Enterprise (1 Gbps)</option>
                  </select>
                </div>

                <div className='flex gap-3 justify-end pt-4'>
                  <button
                    type='button'
                    onClick={() => setIsOpen(false)}
                    className='px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200'
                  >
                    Cancel
                  </button>
                  <button
                    type='submit'
                    disabled={loading}
                    className='px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50'
                  >
                    {loading ? 'Creating...' : 'Create Customer'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

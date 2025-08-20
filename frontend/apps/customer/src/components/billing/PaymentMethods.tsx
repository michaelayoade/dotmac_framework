'use client';

import { useState } from 'react';
import { CreditCardIcon, PlusIcon } from 'lucide-react';
import { addPaymentMethodAction } from '../../app/actions/billing';
import { useRouter } from 'next/navigation';

interface PaymentMethod {
  id: string;
  type: string;
  last4: string;
  expiryMonth: string;
  expiryYear: string;
  isDefault: boolean;
}

export function PaymentMethods({ methods }: { methods: PaymentMethod[] }) {
  const [isAdding, setIsAdding] = useState(false);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleAddMethod = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    
    const formData = new FormData(e.currentTarget);
    const result = await addPaymentMethodAction(formData);
    
    setLoading(false);
    
    if (result.success) {
      setIsAdding(false);
      router.refresh();
    } else {
      alert(result.error || 'Failed to add payment method');
    }
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-lg font-medium text-gray-900">Payment Methods</h2>
        <button
          onClick={() => setIsAdding(true)}
          className="text-sm text-blue-600 hover:text-blue-500"
        >
          <PlusIcon className="h-4 w-4 inline mr-1" />
          Add
        </button>
      </div>
      
      <div className="p-6 space-y-3">
        {methods.map((method) => (
          <div key={method.id} className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
            <div className="flex items-center">
              <CreditCardIcon className="h-5 w-5 text-gray-400 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-900">
                  •••• {method.last4}
                </p>
                <p className="text-xs text-gray-500">
                  Expires {method.expiryMonth}/{method.expiryYear}
                </p>
              </div>
            </div>
            {method.isDefault && (
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                Default
              </span>
            )}
          </div>
        ))}
        
        {methods.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-4">
            No payment methods added yet
          </p>
        )}
      </div>
      
      {isAdding && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-screen items-center justify-center p-4">
            <div className="fixed inset-0 bg-black/50" onClick={() => setIsAdding(false)} />
            
            <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-medium mb-4">Add Payment Method</h3>
              
              <form onSubmit={handleAddMethod} className="space-y-4">
                <div>
                  <label htmlFor="cardNumber" className="block text-sm font-medium text-gray-700">
                    Card Number
                  </label>
                  <input
                    type="text"
                    name="cardNumber"
                    id="cardNumber"
                    required
                    placeholder="1234 5678 9012 3456"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="expiryMonth" className="block text-sm font-medium text-gray-700">
                      Expiry Month
                    </label>
                    <input
                      type="text"
                      name="expiryMonth"
                      id="expiryMonth"
                      required
                      placeholder="MM"
                      maxLength={2}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    />
                  </div>
                  
                  <div>
                    <label htmlFor="expiryYear" className="block text-sm font-medium text-gray-700">
                      Expiry Year
                    </label>
                    <input
                      type="text"
                      name="expiryYear"
                      id="expiryYear"
                      required
                      placeholder="YY"
                      maxLength={2}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    />
                  </div>
                </div>
                
                <div>
                  <label htmlFor="cvv" className="block text-sm font-medium text-gray-700">
                    CVV
                  </label>
                  <input
                    type="text"
                    name="cvv"
                    id="cvv"
                    required
                    placeholder="123"
                    maxLength={4}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  />
                </div>
                
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    name="isDefault"
                    id="isDefault"
                    value="true"
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="isDefault" className="ml-2 block text-sm text-gray-900">
                    Set as default payment method
                  </label>
                </div>
                
                <input type="hidden" name="type" value="card" />
                
                <div className="flex gap-3 justify-end pt-4">
                  <button
                    type="button"
                    onClick={() => setIsAdding(false)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    {loading ? 'Adding...' : 'Add Card'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
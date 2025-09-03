'use client';

import { Card } from '@dotmac/ui/reseller';
import { zodResolver } from '@hookform/resolvers/zod';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Building,
  Calculator,
  Calendar,
  Check,
  Clock,
  Copy,
  DollarSign,
  Download,
  Edit3,
  FileText,
  Mail,
  MapPin,
  Minus,
  Package,
  Percent,
  Phone,
  Plus,
  Save,
  Share,
  Target,
  Users,
  X,
} from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

// Form schemas
const quoteSchema = z.object({
  customerName: z.string().min(1, 'Customer name is required'),
  customerEmail: z.string().email('Valid email is required'),
  customerPhone: z.string().min(10, 'Valid phone number is required'),
  customerAddress: z.string().min(1, 'Address is required'),
  services: z
    .array(
      z.object({
        type: z.string(),
        speed: z.string(),
        price: z.number(),
        installation: z.number(),
        quantity: z.number().min(1),
      })
    )
    .min(1, 'At least one service required'),
  contractTerm: z.number().min(12).max(36),
  discount: z.number().min(0).max(50),
  validUntil: z.string(),
});

type QuoteForm = z.infer<typeof quoteSchema>;

// Service catalog
const serviceTypes = [
  {
    id: 'residential',
    name: 'Residential Internet',
    plans: [
      { speed: '50/10 Mbps', price: 49.99, installation: 99, type: 'Basic' },
      {
        speed: '100/20 Mbps',
        price: 69.99,
        installation: 99,
        type: 'Standard',
      },
      { speed: '500/500 Mbps', price: 99.99, installation: 149, type: 'Fiber' },
      {
        speed: '1000/1000 Mbps',
        price: 129.99,
        installation: 149,
        type: 'Fiber Premium',
      },
    ],
  },
  {
    id: 'business',
    name: 'Business Internet',
    plans: [
      {
        speed: '100/100 Mbps',
        price: 149.99,
        installation: 199,
        type: 'Business Basic',
      },
      {
        speed: '500/500 Mbps',
        price: 249.99,
        installation: 299,
        type: 'Business Pro',
      },
      {
        speed: '1000/1000 Mbps',
        price: 399.99,
        installation: 399,
        type: 'Business Premium',
      },
      {
        speed: '2000/2000 Mbps',
        price: 599.99,
        installation: 499,
        type: 'Enterprise',
      },
    ],
  },
];

// Contract templates
const contractTemplates = [
  {
    id: 'residential-standard',
    name: 'Residential Standard Agreement',
    type: 'Residential',
    description: 'Standard residential internet service agreement',
    terms: '12-24 months',
    features: ['Basic SLA', 'Standard Support', 'Auto-payment discount'],
  },
  {
    id: 'business-basic',
    name: 'Business Basic Agreement',
    type: 'Business',
    description: 'Small business internet service agreement',
    terms: '24-36 months',
    features: ['Business SLA', 'Priority Support', 'Static IP included'],
  },
  {
    id: 'enterprise',
    name: 'Enterprise Service Agreement',
    type: 'Enterprise',
    description: 'Custom enterprise-grade service agreement',
    terms: '36 months+',
    features: ['Custom SLA', '24/7 Support', 'Dedicated Account Manager', 'Redundancy Options'],
  },
];

export function SalesTools() {
  const [activeTab, setActiveTab] = useState<'quote' | 'contracts' | 'calculator'>('quote');
  const [selectedServices, setSelectedServices] = useState<any[]>([]);
  const [generatedQuote, setGeneratedQuote] = useState<any>(null);
  const [selectedContract, setSelectedContract] = useState<string>('');

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
    reset,
  } = useForm<QuoteForm>({
    resolver: zodResolver(quoteSchema),
    defaultValues: {
      services: [],
      contractTerm: 24,
      discount: 0,
      validUntil: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    },
  });

  const addService = (serviceType: string, plan: any) => {
    const newService = {
      id: Date.now(),
      type: serviceType,
      speed: plan.speed,
      price: plan.price,
      installation: plan.installation,
      planType: plan.type,
      quantity: 1,
    };
    setSelectedServices([...selectedServices, newService]);
  };

  const removeService = (serviceId: number) => {
    setSelectedServices(selectedServices.filter((s) => s.id !== serviceId));
  };

  const updateServiceQuantity = (serviceId: number, quantity: number) => {
    if (quantity < 1) return;
    setSelectedServices(selectedServices.map((s) => (s.id === serviceId ? { ...s, quantity } : s)));
  };

  const calculateTotals = () => {
    const subtotal = selectedServices.reduce(
      (sum, service) => sum + service.price * service.quantity,
      0
    );
    const installationTotal = selectedServices.reduce(
      (sum, service) => sum + service.installation * service.quantity,
      0
    );
    const discount = watch('discount') || 0;
    const discountAmount = subtotal * (discount / 100);
    const monthlyTotal = subtotal - discountAmount;
    const contractTerm = watch('contractTerm') || 24;
    const totalContractValue = monthlyTotal * contractTerm;

    return {
      subtotal,
      installationTotal,
      discount,
      discountAmount,
      monthlyTotal,
      totalContractValue,
    };
  };

  const onSubmit = (data: QuoteForm) => {
    const totals = calculateTotals();
    const quote = {
      ...data,
      services: selectedServices,
      totals,
      quoteNumber: `Q-${Date.now()}`,
      createdAt: new Date().toISOString(),
      createdBy: 'Sales Rep', // Would come from auth context
    };
    setGeneratedQuote(quote);
  };

  const tabs = [
    { id: 'quote', label: 'Quote Generator', icon: FileText },
    { id: 'contracts', label: 'Contract Templates', icon: Building },
    { id: 'calculator', label: 'ROI Calculator', icon: Calculator },
  ];

  return (
    <div className='space-y-6'>
      {/* Tab Navigation */}
      <Card className='p-6'>
        <div className='flex space-x-1 bg-gray-100 rounded-lg p-1'>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex-1 flex items-center justify-center space-x-2 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-white text-green-700 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <tab.icon className='w-4 h-4' />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </Card>

      <AnimatePresence mode='wait'>
        {/* Quote Generator */}
        {activeTab === 'quote' && (
          <motion.div
            key='quote'
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className='space-y-6'
          >
            {!generatedQuote ? (
              <div className='grid grid-cols-1 lg:grid-cols-3 gap-6'>
                {/* Quote Form */}
                <div className='lg:col-span-2 space-y-6'>
                  <Card className='p-6'>
                    <h3 className='text-lg font-semibold text-gray-900 mb-4'>
                      Customer Information
                    </h3>
                    <form onSubmit={handleSubmit(onSubmit)} className='space-y-4'>
                      <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                        <div>
                          <label className='block text-sm font-medium text-gray-700 mb-1'>
                            Customer Name
                          </label>
                          <input
                            {...register('customerName')}
                            className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
                            placeholder='John Smith'
                          />
                          {errors.customerName && (
                            <p className='text-red-600 text-xs mt-1'>
                              {errors.customerName.message}
                            </p>
                          )}
                        </div>

                        <div>
                          <label className='block text-sm font-medium text-gray-700 mb-1'>
                            Email
                          </label>
                          <input
                            {...register('customerEmail')}
                            type='email'
                            className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
                            placeholder='test@dev.local'
                          />
                          {errors.customerEmail && (
                            <p className='text-red-600 text-xs mt-1'>
                              {errors.customerEmail.message}
                            </p>
                          )}
                        </div>

                        <div>
                          <label className='block text-sm font-medium text-gray-700 mb-1'>
                            Phone
                          </label>
                          <input
                            {...register('customerPhone')}
                            className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
                            placeholder='+1 (555) 123-4567'
                          />
                          {errors.customerPhone && (
                            <p className='text-red-600 text-xs mt-1'>
                              {errors.customerPhone.message}
                            </p>
                          )}
                        </div>

                        <div>
                          <label className='block text-sm font-medium text-gray-700 mb-1'>
                            Contract Term (months)
                          </label>
                          <select
                            {...register('contractTerm', {
                              valueAsNumber: true,
                            })}
                            className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
                          >
                            <option value={12}>12 months</option>
                            <option value={24}>24 months</option>
                            <option value={36}>36 months</option>
                          </select>
                        </div>
                      </div>

                      <div>
                        <label className='block text-sm font-medium text-gray-700 mb-1'>
                          Address
                        </label>
                        <input
                          {...register('customerAddress')}
                          className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
                          placeholder='123 Main St, City, State 12345'
                        />
                        {errors.customerAddress && (
                          <p className='text-red-600 text-xs mt-1'>
                            {errors.customerAddress.message}
                          </p>
                        )}
                      </div>

                      <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                        <div>
                          <label className='block text-sm font-medium text-gray-700 mb-1'>
                            Discount (%)
                          </label>
                          <input
                            {...register('discount', { valueAsNumber: true })}
                            type='number'
                            min='0'
                            max='50'
                            className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
                            placeholder='0'
                          />
                        </div>

                        <div>
                          <label className='block text-sm font-medium text-gray-700 mb-1'>
                            Valid Until
                          </label>
                          <input
                            {...register('validUntil')}
                            type='date'
                            className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
                          />
                        </div>
                      </div>
                    </form>
                  </Card>

                  {/* Service Selection */}
                  <Card className='p-6'>
                    <h3 className='text-lg font-semibold text-gray-900 mb-4'>Select Services</h3>
                    <div className='space-y-6'>
                      {serviceTypes.map((serviceType) => (
                        <div key={serviceType.id}>
                          <h4 className='text-md font-medium text-gray-800 mb-3'>
                            {serviceType.name}
                          </h4>
                          <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                            {serviceType.plans.map((plan) => (
                              <div
                                key={plan.type}
                                className='border border-gray-200 rounded-lg p-4 hover:border-green-300 cursor-pointer'
                                onClick={() => addService(serviceType.id, plan)}
                              >
                                <div className='flex justify-between items-start mb-2'>
                                  <h5 className='font-medium text-gray-900'>{plan.type}</h5>
                                  <span className='text-green-600 font-semibold'>
                                    ${plan.price}/mo
                                  </span>
                                </div>
                                <p className='text-gray-600 text-sm mb-2'>{plan.speed}</p>
                                <p className='text-gray-500 text-xs'>
                                  Installation: ${plan.installation}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>

                  {/* Generate Quote Button */}
                  {selectedServices.length > 0 && (
                    <Card className='p-6'>
                      <button
                        onClick={handleSubmit(onSubmit)}
                        className='w-full flex items-center justify-center space-x-2 bg-green-600 text-white py-3 px-6 rounded-lg hover:bg-green-700 font-medium'
                      >
                        <FileText className='w-5 h-5' />
                        <span>Generate Quote</span>
                      </button>
                    </Card>
                  )}
                </div>

                {/* Selected Services & Preview */}
                <div className='space-y-6'>
                  <Card className='p-6'>
                    <h3 className='text-lg font-semibold text-gray-900 mb-4'>Selected Services</h3>
                    {selectedServices.length === 0 ? (
                      <p className='text-gray-500 text-center py-8'>No services selected yet</p>
                    ) : (
                      <div className='space-y-3'>
                        {selectedServices.map((service) => (
                          <div
                            key={service.id}
                            className='flex items-center justify-between p-3 bg-gray-50 rounded-lg'
                          >
                            <div className='flex-1'>
                              <h4 className='font-medium text-gray-900'>{service.planType}</h4>
                              <p className='text-gray-600 text-sm'>{service.speed}</p>
                            </div>
                            <div className='flex items-center space-x-2'>
                              <button
                                onClick={() =>
                                  updateServiceQuantity(service.id, service.quantity - 1)
                                }
                                className='p-1 text-gray-400 hover:text-gray-600'
                              >
                                <Minus className='w-4 h-4' />
                              </button>
                              <span className='w-8 text-center'>{service.quantity}</span>
                              <button
                                onClick={() =>
                                  updateServiceQuantity(service.id, service.quantity + 1)
                                }
                                className='p-1 text-gray-400 hover:text-gray-600'
                              >
                                <Plus className='w-4 h-4' />
                              </button>
                              <button
                                onClick={() => removeService(service.id)}
                                className='p-1 text-red-400 hover:text-red-600 ml-2'
                              >
                                <X className='w-4 h-4' />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>

                  {selectedServices.length > 0 && (
                    <Card className='p-6'>
                      <h3 className='text-lg font-semibold text-gray-900 mb-4'>Quote Summary</h3>
                      <div className='space-y-3'>
                        {(() => {
                          const totals = calculateTotals();
                          return (
                            <>
                              <div className='flex justify-between'>
                                <span className='text-gray-600'>Monthly Subtotal:</span>
                                <span className='font-medium'>${totals.subtotal.toFixed(2)}</span>
                              </div>
                              {totals.discount > 0 && (
                                <div className='flex justify-between text-green-600'>
                                  <span>Discount ({totals.discount}%):</span>
                                  <span>-${totals.discountAmount.toFixed(2)}</span>
                                </div>
                              )}
                              <div className='flex justify-between font-semibold text-lg border-t pt-2'>
                                <span>Monthly Total:</span>
                                <span>${totals.monthlyTotal.toFixed(2)}</span>
                              </div>
                              <div className='flex justify-between text-gray-600'>
                                <span>Installation:</span>
                                <span>${totals.installationTotal.toFixed(2)}</span>
                              </div>
                              <div className='flex justify-between text-gray-600'>
                                <span>Total Contract Value:</span>
                                <span className='font-semibold'>
                                  ${totals.totalContractValue.toFixed(2)}
                                </span>
                              </div>
                            </>
                          );
                        })()}
                      </div>
                    </Card>
                  )}
                </div>
              </div>
            ) : (
              /* Generated Quote Display */
              <Card className='p-8'>
                <div className='max-w-3xl mx-auto'>
                  <div className='text-center mb-8'>
                    <h2 className='text-2xl font-bold text-gray-900'>Internet Service Quote</h2>
                    <p className='text-gray-600 mt-2'>Quote #{generatedQuote.quoteNumber}</p>
                  </div>

                  <div className='grid grid-cols-1 md:grid-cols-2 gap-8 mb-8'>
                    <div>
                      <h3 className='font-semibold text-gray-900 mb-3'>Customer Information</h3>
                      <div className='space-y-2 text-sm'>
                        <p>
                          <strong>Name:</strong> {generatedQuote.customerName}
                        </p>
                        <p>
                          <strong>Email:</strong> {generatedQuote.customerEmail}
                        </p>
                        <p>
                          <strong>Phone:</strong> {generatedQuote.customerPhone}
                        </p>
                        <p>
                          <strong>Address:</strong> {generatedQuote.customerAddress}
                        </p>
                      </div>
                    </div>

                    <div>
                      <h3 className='font-semibold text-gray-900 mb-3'>Quote Details</h3>
                      <div className='space-y-2 text-sm'>
                        <p>
                          <strong>Contract Term:</strong> {generatedQuote.contractTerm} months
                        </p>
                        <p>
                          <strong>Valid Until:</strong>{' '}
                          {new Date(generatedQuote.validUntil).toLocaleDateString()}
                        </p>
                        <p>
                          <strong>Created:</strong>{' '}
                          {new Date(generatedQuote.createdAt).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className='mb-8'>
                    <h3 className='font-semibold text-gray-900 mb-4'>Services</h3>
                    <div className='overflow-x-auto'>
                      <table className='w-full border-collapse border border-gray-300'>
                        <thead>
                          <tr className='bg-gray-50'>
                            <th className='border border-gray-300 px-4 py-2 text-left'>Service</th>
                            <th className='border border-gray-300 px-4 py-2 text-right'>Speed</th>
                            <th className='border border-gray-300 px-4 py-2 text-right'>Qty</th>
                            <th className='border border-gray-300 px-4 py-2 text-right'>Monthly</th>
                            <th className='border border-gray-300 px-4 py-2 text-right'>
                              Installation
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {generatedQuote.services.map((service: any) => (
                            <tr key={service.id}>
                              <td className='border border-gray-300 px-4 py-2'>
                                {service.planType}
                              </td>
                              <td className='border border-gray-300 px-4 py-2 text-right'>
                                {service.speed}
                              </td>
                              <td className='border border-gray-300 px-4 py-2 text-right'>
                                {service.quantity}
                              </td>
                              <td className='border border-gray-300 px-4 py-2 text-right'>
                                ${(service.price * service.quantity).toFixed(2)}
                              </td>
                              <td className='border border-gray-300 px-4 py-2 text-right'>
                                ${(service.installation * service.quantity).toFixed(2)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className='bg-gray-50 p-6 rounded-lg'>
                    <div className='space-y-2'>
                      <div className='flex justify-between'>
                        <span>Monthly Subtotal:</span>
                        <span>${generatedQuote.totals.subtotal.toFixed(2)}</span>
                      </div>
                      {generatedQuote.totals.discount > 0 && (
                        <div className='flex justify-between text-green-600'>
                          <span>Discount ({generatedQuote.totals.discount}%):</span>
                          <span>-${generatedQuote.totals.discountAmount.toFixed(2)}</span>
                        </div>
                      )}
                      <div className='flex justify-between font-semibold text-lg border-t pt-2'>
                        <span>Monthly Total:</span>
                        <span>${generatedQuote.totals.monthlyTotal.toFixed(2)}</span>
                      </div>
                      <div className='flex justify-between'>
                        <span>One-time Installation:</span>
                        <span>${generatedQuote.totals.installationTotal.toFixed(2)}</span>
                      </div>
                      <div className='flex justify-between font-bold text-xl border-t pt-2'>
                        <span>Total Contract Value:</span>
                        <span>${generatedQuote.totals.totalContractValue.toFixed(2)}</span>
                      </div>
                    </div>
                  </div>

                  <div className='flex justify-center space-x-4 mt-8'>
                    <button
                      onClick={() => setGeneratedQuote(null)}
                      className='flex items-center space-x-2 px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50'
                    >
                      <Edit3 className='w-4 h-4' />
                      <span>Edit Quote</span>
                    </button>
                    <button className='flex items-center space-x-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700'>
                      <Download className='w-4 h-4' />
                      <span>Download PDF</span>
                    </button>
                    <button className='flex items-center space-x-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700'>
                      <Share className='w-4 h-4' />
                      <span>Send Quote</span>
                    </button>
                  </div>
                </div>
              </Card>
            )}
          </motion.div>
        )}

        {/* Contract Templates */}
        {activeTab === 'contracts' && (
          <motion.div
            key='contracts'
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <Card className='p-6'>
              <div className='flex items-center justify-between mb-6'>
                <h3 className='text-lg font-semibold text-gray-900'>Contract Templates</h3>
                <button className='flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700'>
                  <Plus className='w-4 h-4' />
                  <span>New Template</span>
                </button>
              </div>

              <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
                {contractTemplates.map((template) => (
                  <div
                    key={template.id}
                    className={`border rounded-lg p-6 cursor-pointer transition-colors ${
                      selectedContract === template.id
                        ? 'border-green-500 bg-green-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => setSelectedContract(template.id)}
                  >
                    <div className='flex items-center justify-between mb-3'>
                      <h4 className='font-semibold text-gray-900'>{template.name}</h4>
                      <span className='text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full'>
                        {template.type}
                      </span>
                    </div>
                    <p className='text-gray-600 text-sm mb-3'>{template.description}</p>
                    <div className='text-xs text-gray-500 mb-4'>
                      <strong>Terms:</strong> {template.terms}
                    </div>
                    <div className='space-y-1'>
                      {template.features.map((feature) => (
                        <div key={feature} className='flex items-center text-xs text-gray-600'>
                          <Check className='w-3 h-3 text-green-500 mr-1' />
                          <span>{feature}</span>
                        </div>
                      ))}
                    </div>
                    <div className='mt-4 flex space-x-2'>
                      <button className='flex-1 text-xs bg-gray-100 text-gray-700 py-2 px-3 rounded hover:bg-gray-200'>
                        Preview
                      </button>
                      <button className='flex-1 text-xs bg-green-600 text-white py-2 px-3 rounded hover:bg-green-700'>
                        Use Template
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </motion.div>
        )}

        {/* ROI Calculator */}
        {activeTab === 'calculator' && (
          <motion.div
            key='calculator'
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
              <Card className='p-6'>
                <h3 className='text-lg font-semibold text-gray-900 mb-4'>ROI Calculator</h3>
                <div className='space-y-4'>
                  <div>
                    <label className='block text-sm font-medium text-gray-700 mb-1'>
                      Initial Investment ($)
                    </label>
                    <input
                      type='number'
                      className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
                      placeholder='5000'
                    />
                  </div>

                  <div>
                    <label className='block text-sm font-medium text-gray-700 mb-1'>
                      Monthly Revenue per Customer ($)
                    </label>
                    <input
                      type='number'
                      className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
                      placeholder='150'
                    />
                  </div>

                  <div>
                    <label className='block text-sm font-medium text-gray-700 mb-1'>
                      Expected Customers (first year)
                    </label>
                    <input
                      type='number'
                      className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
                      placeholder='50'
                    />
                  </div>

                  <div>
                    <label className='block text-sm font-medium text-gray-700 mb-1'>
                      Commission Rate (%)
                    </label>
                    <input
                      type='number'
                      className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
                      placeholder='10'
                    />
                  </div>

                  <div>
                    <label className='block text-sm font-medium text-gray-700 mb-1'>
                      Customer Retention Rate (%)
                    </label>
                    <input
                      type='number'
                      className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
                      placeholder='85'
                    />
                  </div>

                  <button className='w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 font-medium'>
                    Calculate ROI
                  </button>
                </div>
              </Card>

              <Card className='p-6'>
                <h3 className='text-lg font-semibold text-gray-900 mb-4'>ROI Projection</h3>
                <div className='space-y-6'>
                  <div className='bg-green-50 p-4 rounded-lg'>
                    <div className='text-center'>
                      <div className='text-3xl font-bold text-green-600'>247%</div>
                      <div className='text-sm text-green-700'>1-Year ROI</div>
                    </div>
                  </div>

                  <div className='grid grid-cols-2 gap-4'>
                    <div className='text-center p-3 bg-gray-50 rounded-lg'>
                      <div className='text-xl font-semibold text-gray-900'>$18,000</div>
                      <div className='text-xs text-gray-600'>Annual Revenue</div>
                    </div>
                    <div className='text-center p-3 bg-gray-50 rounded-lg'>
                      <div className='text-xl font-semibold text-gray-900'>$1,800</div>
                      <div className='text-xs text-gray-600'>Annual Commission</div>
                    </div>
                  </div>

                  <div>
                    <h4 className='font-medium text-gray-900 mb-3'>Breakdown by Quarter</h4>
                    <div className='space-y-2'>
                      {['Q1', 'Q2', 'Q3', 'Q4'].map((quarter, index) => (
                        <div
                          key={quarter}
                          className='flex justify-between items-center py-2 border-b border-gray-100'
                        >
                          <span className='text-sm text-gray-700'>{quarter}</span>
                          <div className='text-right'>
                            <div className='text-sm font-medium text-gray-900'>
                              ${(450 + index * 150).toFixed(0)}
                            </div>
                            <div className='text-xs text-gray-600'>Commission</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className='pt-4 border-t border-gray-200'>
                    <div className='flex justify-between items-center'>
                      <span className='font-medium text-gray-900'>Break-even Point:</span>
                      <span className='font-semibold text-green-600'>Month 8</span>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

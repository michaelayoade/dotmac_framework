"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import {
  CheckCircle,
  ChevronRight,
  ChevronLeft,
  User,
  CreditCard,
  Wifi,
  Bell,
  MapPin,
  Phone,
  Mail,
  Shield,
  Clock,
  DollarSign,
  Star,
} from "lucide-react";

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  required: boolean;
}

interface ServicePlan {
  id: string;
  name: string;
  speed: string;
  price: number;
  features: string[];
  recommended?: boolean;
}

interface PaymentMethod {
  id: string;
  type: "card" | "ach" | "manual";
  name: string;
  description: string;
  processingTime: string;
}

const onboardingSteps: OnboardingStep[] = [
  {
    id: "welcome",
    title: "Welcome",
    description: "Let's get your internet service set up",
    icon: User,
    required: true,
  },
  {
    id: "profile",
    title: "Profile Setup", 
    description: "Complete your account information",
    icon: User,
    required: true,
  },
  {
    id: "address",
    title: "Service Address",
    description: "Confirm your service installation address", 
    icon: MapPin,
    required: true,
  },
  {
    id: "service-plan",
    title: "Choose Plan",
    description: "Select your internet service plan",
    icon: Wifi,
    required: true,
  },
  {
    id: "payment",
    title: "Payment Setup",
    description: "Set up your billing and payment method",
    icon: CreditCard,
    required: true,
  },
  {
    id: "preferences",
    title: "Preferences",
    description: "Configure notifications and preferences",
    icon: Bell,
    required: false,
  },
  {
    id: "complete",
    title: "Complete",
    description: "Your service is ready to activate",
    icon: CheckCircle,
    required: true,
  },
];

const servicePlans: ServicePlan[] = [
  {
    id: "basic",
    name: "Essential",
    speed: "25/5 Mbps",
    price: 39.99,
    features: ["Perfect for browsing and email", "1-2 devices", "Basic support"],
  },
  {
    id: "standard", 
    name: "Home Pro",
    speed: "100/20 Mbps", 
    price: 59.99,
    features: ["Great for streaming and gaming", "3-5 devices", "Priority support"],
    recommended: true,
  },
  {
    id: "premium",
    name: "Gigabit",
    speed: "1000/100 Mbps",
    price: 99.99,
    features: ["Ultra-fast for everything", "10+ devices", "Premium support", "Static IP available"],
  },
];

const paymentMethods: PaymentMethod[] = [
  {
    id: "card",
    type: "card",
    name: "Credit/Debit Card",
    description: "Instant processing, most convenient",
    processingTime: "Instant",
  },
  {
    id: "ach",
    type: "ach", 
    name: "Bank Transfer (ACH)",
    description: "Direct from your bank account",
    processingTime: "2-3 business days",
  },
  {
    id: "manual",
    type: "manual",
    name: "Manual Payment",
    description: "Pay by check or in person",
    processingTime: "Manual processing",
  },
];

export default function CustomerOnboardingPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form data
  const [formData, setFormData] = useState({
    // Profile
    firstName: "",
    lastName: "",
    phone: "",
    email: "",
    
    // Address
    streetAddress: "",
    apt: "",
    city: "",
    state: "",
    zipCode: "",
    
    // Service
    selectedPlan: "",
    installationDate: "",
    installationTime: "",
    
    // Payment
    paymentMethod: "",
    cardNumber: "",
    expiryDate: "",
    cvv: "",
    billingName: "",
    
    // Preferences
    emailNotifications: true,
    smsNotifications: true,
    marketingEmails: false,
    paperlessBilling: true,
  });

  // Check if step is completed
  const isStepCompleted = (stepId: string): boolean => {
    return completedSteps.has(stepId);
  };

  // Mark step as completed
  const markStepCompleted = (stepId: string) => {
    setCompletedSteps(prev => new Set([...prev, stepId]));
  };

  // Validate current step
  const validateCurrentStep = (): boolean => {
    const step = onboardingSteps[currentStep];
    
    switch (step.id) {
      case "profile":
        return formData.firstName && formData.lastName && formData.phone && formData.email;
      case "address":
        return formData.streetAddress && formData.city && formData.state && formData.zipCode;
      case "service-plan":
        return !!formData.selectedPlan;
      case "payment":
        return formData.paymentMethod && (
          formData.paymentMethod === "manual" || 
          (formData.cardNumber && formData.expiryDate && formData.cvv && formData.billingName)
        );
      default:
        return true;
    }
  };

  // Handle next step
  const handleNext = async () => {
    if (!validateCurrentStep()) {
      setError("Please complete all required fields");
      return;
    }

    setError(null);
    
    // Mark current step as completed
    const currentStepId = onboardingSteps[currentStep].id;
    markStepCompleted(currentStepId);

    // Move to next step
    if (currentStep < onboardingSteps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  // Handle previous step
  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  // Handle final completion
  const handleComplete = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Submit onboarding data
      const response = await fetch("/api/customer/onboarding", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          profile: {
            firstName: formData.firstName,
            lastName: formData.lastName,
            phone: formData.phone,
            email: formData.email,
          },
          address: {
            streetAddress: formData.streetAddress,
            apt: formData.apt,
            city: formData.city,
            state: formData.state,
            zipCode: formData.zipCode,
          },
          service: {
            planId: formData.selectedPlan,
            installationDate: formData.installationDate,
            installationTime: formData.installationTime,
          },
          payment: {
            method: formData.paymentMethod,
            billingName: formData.billingName,
            // Note: In production, never send sensitive payment data to frontend
          },
          preferences: {
            emailNotifications: formData.emailNotifications,
            smsNotifications: formData.smsNotifications,
            marketingEmails: formData.marketingEmails,
            paperlessBilling: formData.paperlessBilling,
          },
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to complete onboarding");
      }

      // Redirect to dashboard with success message
      router.push("/?onboarding=complete");

    } catch (err: any) {
      setError(err.message || "Failed to complete onboarding");
    } finally {
      setIsLoading(false);
    }
  };

  // Render step content
  const renderStepContent = () => {
    const step = onboardingSteps[currentStep];

    switch (step.id) {
      case "welcome":
        return (
          <div className="text-center py-8">
            <div className="bg-blue-100 rounded-full w-20 h-20 flex items-center justify-center mx-auto mb-6">
              <Wifi className="h-10 w-10 text-blue-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Welcome to DotMac ISP!</h2>
            <p className="text-gray-600 text-lg mb-8">
              Let's get your high-speed internet service set up. This should only take a few minutes.
            </p>
            <div className="bg-blue-50 rounded-lg p-6 border border-blue-200">
              <h3 className="font-semibold text-gray-900 mb-3">What we'll cover:</h3>
              <div className="grid md:grid-cols-2 gap-4 text-left">
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                  <span>Complete your profile</span>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                  <span>Choose your service plan</span>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                  <span>Set up billing and payment</span>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                  <span>Configure your preferences</span>
                </div>
              </div>
            </div>
          </div>
        );

      case "profile":
        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <User className="h-12 w-12 text-blue-600 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900">Complete Your Profile</h2>
              <p className="text-gray-600">This information helps us provide you with better service</p>
            </div>
            
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  First Name *
                </label>
                <Input
                  value={formData.firstName}
                  onChange={(e) => setFormData({...formData, firstName: e.target.value})}
                  placeholder="Enter your first name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Last Name *
                </label>
                <Input
                  value={formData.lastName}
                  onChange={(e) => setFormData({...formData, lastName: e.target.value})}
                  placeholder="Enter your last name"
                />
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Phone Number *
                </label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <Input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData({...formData, phone: e.target.value})}
                    placeholder="(555) 123-4567"
                    className="pl-10"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email Address *
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    placeholder="your.email@example.com"
                    className="pl-10"
                  />
                </div>
              </div>
            </div>
          </div>
        );

      case "address":
        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <MapPin className="h-12 w-12 text-blue-600 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900">Service Address</h2>
              <p className="text-gray-600">Where should we install your internet service?</p>
            </div>

            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Street Address *
                </label>
                <Input
                  value={formData.streetAddress}
                  onChange={(e) => setFormData({...formData, streetAddress: e.target.value})}
                  placeholder="123 Main Street"
                />
              </div>

              <div className="grid md:grid-cols-3 gap-4">
                <div className="md:col-span-1">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Apt/Suite
                  </label>
                  <Input
                    value={formData.apt}
                    onChange={(e) => setFormData({...formData, apt: e.target.value})}
                    placeholder="Apt 4B"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    City *
                  </label>
                  <Input
                    value={formData.city}
                    onChange={(e) => setFormData({...formData, city: e.target.value})}
                    placeholder="Your city"
                  />
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    State *
                  </label>
                  <Input
                    value={formData.state}
                    onChange={(e) => setFormData({...formData, state: e.target.value})}
                    placeholder="CA"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    ZIP Code *
                  </label>
                  <Input
                    value={formData.zipCode}
                    onChange={(e) => setFormData({...formData, zipCode: e.target.value})}
                    placeholder="90210"
                  />
                </div>
              </div>
            </div>
          </div>
        );

      case "service-plan":
        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <Wifi className="h-12 w-12 text-blue-600 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900">Choose Your Plan</h2>
              <p className="text-gray-600">Select the internet speed that's right for you</p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              {servicePlans.map((plan) => (
                <Card
                  key={plan.id}
                  className={`cursor-pointer transition-all ${
                    formData.selectedPlan === plan.id
                      ? "ring-2 ring-blue-500 border-blue-300"
                      : "hover:shadow-lg hover:border-gray-300"
                  } ${plan.recommended ? "relative" : ""}`}
                  onClick={() => setFormData({...formData, selectedPlan: plan.id})}
                >
                  {plan.recommended && (
                    <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                      <div className="bg-blue-600 text-white px-3 py-1 rounded-full text-sm font-medium flex items-center">
                        <Star className="h-4 w-4 mr-1" />
                        Most Popular
                      </div>
                    </div>
                  )}
                  
                  <div className="p-6">
                    <h3 className="text-xl font-bold text-gray-900 mb-2">{plan.name}</h3>
                    <div className="text-3xl font-bold text-blue-600 mb-1">
                      ${plan.price}
                      <span className="text-lg text-gray-600 font-normal">/mo</span>
                    </div>
                    <p className="text-gray-600 mb-4">{plan.speed}</p>
                    
                    <ul className="space-y-2">
                      {plan.features.map((feature, index) => (
                        <li key={index} className="flex items-center text-sm text-gray-600">
                          <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        );

      case "payment":
        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <CreditCard className="h-12 w-12 text-blue-600 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900">Payment Setup</h2>
              <p className="text-gray-600">Choose how you'd like to pay for your service</p>
            </div>

            {/* Payment Method Selection */}
            <div className="space-y-4">
              <h3 className="font-semibold text-gray-900">Payment Method</h3>
              {paymentMethods.map((method) => (
                <Card
                  key={method.id}
                  className={`cursor-pointer transition-all ${
                    formData.paymentMethod === method.id
                      ? "ring-2 ring-blue-500 border-blue-300"
                      : "hover:border-gray-300"
                  }`}
                  onClick={() => setFormData({...formData, paymentMethod: method.id})}
                >
                  <div className="p-4 flex items-center justify-between">
                    <div className="flex items-center">
                      <div className={`w-4 h-4 rounded-full border-2 mr-4 ${
                        formData.paymentMethod === method.id
                          ? "bg-blue-600 border-blue-600"
                          : "border-gray-300"
                      }`} />
                      <div>
                        <h4 className="font-medium text-gray-900">{method.name}</h4>
                        <p className="text-sm text-gray-600">{method.description}</p>
                      </div>
                    </div>
                    <div className="text-sm text-gray-500">
                      <Clock className="h-4 w-4 inline mr-1" />
                      {method.processingTime}
                    </div>
                  </div>
                </Card>
              ))}
            </div>

            {/* Card Details */}
            {formData.paymentMethod === "card" && (
              <div className="space-y-4">
                <h3 className="font-semibold text-gray-900">Card Information</h3>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Cardholder Name *
                  </label>
                  <Input
                    value={formData.billingName}
                    onChange={(e) => setFormData({...formData, billingName: e.target.value})}
                    placeholder="Name on card"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Card Number *
                  </label>
                  <Input
                    value={formData.cardNumber}
                    onChange={(e) => setFormData({...formData, cardNumber: e.target.value})}
                    placeholder="1234 5678 9012 3456"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Expiry Date *
                    </label>
                    <Input
                      value={formData.expiryDate}
                      onChange={(e) => setFormData({...formData, expiryDate: e.target.value})}
                      placeholder="MM/YY"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      CVV *
                    </label>
                    <Input
                      value={formData.cvv}
                      onChange={(e) => setFormData({...formData, cvv: e.target.value})}
                      placeholder="123"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        );

      case "preferences":
        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <Bell className="h-12 w-12 text-blue-600 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900">Your Preferences</h2>
              <p className="text-gray-600">Customize how we communicate with you</p>
            </div>

            <div className="space-y-6">
              <Card className="p-6">
                <h3 className="font-semibold text-gray-900 mb-4">Communication Preferences</h3>
                <div className="space-y-4">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.emailNotifications}
                      onChange={(e) => setFormData({...formData, emailNotifications: e.target.checked})}
                      className="h-4 w-4 text-blue-600 rounded border-gray-300"
                    />
                    <span className="ml-3">Email notifications for service updates and outages</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.smsNotifications}
                      onChange={(e) => setFormData({...formData, smsNotifications: e.target.checked})}
                      className="h-4 w-4 text-blue-600 rounded border-gray-300"
                    />
                    <span className="ml-3">SMS alerts for urgent service issues</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.marketingEmails}
                      onChange={(e) => setFormData({...formData, marketingEmails: e.target.checked})}
                      className="h-4 w-4 text-blue-600 rounded border-gray-300"
                    />
                    <span className="ml-3">Marketing emails about new services and promotions</span>
                  </label>
                </div>
              </Card>

              <Card className="p-6">
                <h3 className="font-semibold text-gray-900 mb-4">Billing Preferences</h3>
                <div className="space-y-4">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.paperlessBilling}
                      onChange={(e) => setFormData({...formData, paperlessBilling: e.target.checked})}
                      className="h-4 w-4 text-blue-600 rounded border-gray-300"
                    />
                    <span className="ml-3">Paperless billing (receive invoices by email)</span>
                  </label>
                </div>
              </Card>
            </div>
          </div>
        );

      case "complete":
        const selectedPlan = servicePlans.find(p => p.id === formData.selectedPlan);
        return (
          <div className="text-center py-8">
            <div className="bg-green-100 rounded-full w-20 h-20 flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="h-10 w-10 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">You're All Set!</h2>
            <p className="text-gray-600 text-lg mb-8">
              Your service is ready to activate. Here's a summary of your setup:
            </p>

            <div className="bg-gray-50 rounded-lg p-6 text-left mb-8">
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">Service Plan</h3>
                  <p className="text-gray-600">{selectedPlan?.name} - {selectedPlan?.speed}</p>
                  <p className="text-2xl font-bold text-blue-600">${selectedPlan?.price}/month</p>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">Service Address</h3>
                  <p className="text-gray-600">
                    {formData.streetAddress}
                    {formData.apt && `, ${formData.apt}`}
                    <br />
                    {formData.city}, {formData.state} {formData.zipCode}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-blue-50 rounded-lg p-6 border border-blue-200">
              <h3 className="font-semibold text-gray-900 mb-3">Next Steps:</h3>
              <div className="text-left space-y-2">
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                  <span>We'll schedule your installation appointment</span>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                  <span>You'll receive your Portal ID via email</span>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                  <span>Installation technician will contact you</span>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                  <span>Your service will be activated after installation</span>
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  const currentStepObj = onboardingSteps[currentStep];

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Progress Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Service Setup</h1>
              <p className="text-gray-600">
                Step {currentStep + 1} of {onboardingSteps.length}
              </p>
            </div>
            <div className="text-sm text-gray-500">
              {Math.round(((currentStep + 1) / onboardingSteps.length) * 100)}% Complete
            </div>
          </div>

          {/* Progress Bar */}
          <div className="flex items-center space-x-4 mb-6">
            {onboardingSteps.map((step, index) => {
              const Icon = step.icon;
              const isCurrent = index === currentStep;
              const isCompleted = isStepCompleted(step.id);
              const isPassed = index < currentStep;

              return (
                <div key={step.id} className="flex items-center flex-1">
                  <div
                    className={`flex items-center justify-center w-8 h-8 rounded-full ${
                      isCompleted || isCurrent
                        ? "bg-blue-600 text-white"
                        : isPassed
                        ? "bg-green-600 text-white"
                        : "bg-gray-200 text-gray-500"
                    }`}
                  >
                    {isCompleted || isPassed ? (
                      <CheckCircle className="h-5 w-5" />
                    ) : (
                      <Icon className="h-4 w-4" />
                    )}
                  </div>
                  {index < onboardingSteps.length - 1 && (
                    <div
                      className={`flex-1 h-1 mx-2 ${
                        isPassed || isCompleted ? "bg-blue-600" : "bg-gray-200"
                      }`}
                    />
                  )}
                </div>
              );
            })}
          </div>

          {/* Step Title */}
          <div className="text-center">
            <h2 className="text-xl font-semibold text-gray-900">{currentStepObj.title}</h2>
            <p className="text-gray-600">{currentStepObj.description}</p>
          </div>
        </div>

        {/* Main Content */}
        <Card className="p-8 mb-8">
          {error && (
            <Alert variant="error" className="mb-6">
              {error}
            </Alert>
          )}

          {renderStepContent()}
        </Card>

        {/* Navigation */}
        <div className="flex justify-between">
          <Button
            variant="outline"
            onClick={handlePrevious}
            disabled={currentStep === 0}
            className="flex items-center"
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Previous
          </Button>

          <div className="flex space-x-4">
            {currentStep < onboardingSteps.length - 1 ? (
              <Button
                onClick={handleNext}
                disabled={!validateCurrentStep()}
                className="flex items-center"
              >
                Next
                <ChevronRight className="h-4 w-4 ml-2" />
              </Button>
            ) : (
              <Button
                onClick={handleComplete}
                disabled={isLoading || !validateCurrentStep()}
                className="flex items-center bg-green-600 hover:bg-green-700"
              >
                {isLoading ? (
                  <>
                    <LoadingSpinner size="sm" className="mr-2" />
                    Completing Setup...
                  </>
                ) : (
                  <>
                    Complete Setup
                    <CheckCircle className="h-4 w-4 ml-2" />
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
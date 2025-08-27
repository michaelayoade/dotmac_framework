'use client';

import React, { useState, useEffect } from 'react';
import {
  ShieldCheckIcon,
  QrCodeIcon,
  DevicePhoneMobileIcon,
  KeyIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClipboardDocumentIcon,
  EyeIcon,
  EyeSlashIcon
} from '@heroicons/react/24/outline';
import { useMFA, MFAMethod, MFAStatus, TOTPSetup } from '@/lib/mfa-service';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import QRCode from 'qrcode';

interface MFASetupProps {
  onSetupComplete?: () => void;
  onCancel?: () => void;
}

export function MFASetup({ onSetupComplete, onCancel }: MFASetupProps) {
  const { config, loading, setupTOTP, verifyTOTP, validateTOTPCode } = useMFA();
  const [currentStep, setCurrentStep] = useState<'method' | 'setup' | 'verify' | 'backup'>('method');
  const [selectedMethod, setSelectedMethod] = useState<MFAMethod>(MFAMethod.TOTP);
  const [setupData, setSetupData] = useState<TOTPSetup | null>(null);
  const [qrCodeDataUrl, setQrCodeDataUrl] = useState<string>('');
  const [verificationCode, setVerificationCode] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [showSecret, setShowSecret] = useState(false);
  const [setupLoading, setSetupLoading] = useState(false);
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [savedCodes, setSavedCodes] = useState(false);

  useEffect(() => {
    if (setupData?.qrCodeUrl) {
      generateQRCode(setupData.qrCodeUrl);
    }
  }, [setupData]);

  const generateQRCode = async (url: string) => {
    try {
      const dataUrl = await QRCode.toDataURL(url);
      setQrCodeDataUrl(dataUrl);
    } catch (error) {
      console.error('QR code generation failed:', error);
    }
  };

  const handleMethodSelect = (method: MFAMethod) => {
    setSelectedMethod(method);
    setCurrentStep('setup');
    
    if (method === MFAMethod.TOTP) {
      initializeTOTPSetup();
    }
  };

  const initializeTOTPSetup = async () => {
    setSetupLoading(true);
    setError('');

    try {
      const setup = await setupTOTP();
      setSetupData(setup);
      setCurrentStep('verify');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Setup failed');
    } finally {
      setSetupLoading(false);
    }
  };

  const handleVerifyCode = async () => {
    if (!validateTOTPCode(verificationCode)) {
      setError('Please enter a valid 6-digit code');
      return;
    }

    setVerifyLoading(true);
    setError('');

    try {
      const result = await verifyTOTP(verificationCode);
      if (result.success) {
        setBackupCodes(result.backupCodes);
        setCurrentStep('backup');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed');
    } finally {
      setVerifyLoading(false);
    }
  };

  const handleCodeInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
    setVerificationCode(value);
    setError('');
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  };

  const handleFinishSetup = () => {
    if (savedCodes) {
      onSetupComplete?.();
    }
  };

  const renderMethodSelection = () => (
    <div className="space-y-4">
      <div className="text-center mb-6">
        <ShieldCheckIcon className="mx-auto h-12 w-12 text-blue-600 mb-4" />
        <h2 className="text-2xl font-bold text-gray-900">Set up Multi-Factor Authentication</h2>
        <p className="text-gray-600 mt-2">
          Add an extra layer of security to your account by choosing a verification method.
        </p>
      </div>

      <div className="space-y-4">
        <button
          onClick={() => handleMethodSelect(MFAMethod.TOTP)}
          className="w-full p-6 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors text-left"
        >
          <div className="flex items-center space-x-4">
            <QrCodeIcon className="h-8 w-8 text-blue-600" />
            <div>
              <h3 className="text-lg font-medium text-gray-900">Authenticator App</h3>
              <p className="text-sm text-gray-600">
                Use Google Authenticator, Authy, or similar apps to generate codes
              </p>
            </div>
          </div>
        </button>

        <button
          onClick={() => handleMethodSelect(MFAMethod.SMS)}
          className="w-full p-6 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors text-left"
          disabled
        >
          <div className="flex items-center space-x-4">
            <DevicePhoneMobileIcon className="h-8 w-8 text-gray-400" />
            <div>
              <h3 className="text-lg font-medium text-gray-400">SMS Verification</h3>
              <p className="text-sm text-gray-500">
                Receive codes via text message (Coming Soon)
              </p>
            </div>
          </div>
        </button>
      </div>

      {onCancel && (
        <div className="flex justify-end pt-4">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );

  const renderTOTPSetup = () => (
    <div className="space-y-6">
      <div className="text-center">
        <QrCodeIcon className="mx-auto h-12 w-12 text-blue-600 mb-4" />
        <h2 className="text-2xl font-bold text-gray-900">Set up Authenticator App</h2>
        <p className="text-gray-600 mt-2">
          Scan the QR code with your authenticator app to add your account.
        </p>
      </div>

      {setupLoading ? (
        <div className="text-center py-8">
          <LoadingSpinner size="large" />
          <p className="mt-4 text-gray-600">Setting up authenticator...</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* QR Code */}
          <div className="bg-white border-2 border-gray-200 rounded-lg p-6 text-center">
            {qrCodeDataUrl ? (
              <img 
                src={qrCodeDataUrl} 
                alt="QR Code for MFA setup" 
                className="mx-auto mb-4"
                style={{ maxWidth: '200px', maxHeight: '200px' }}
              />
            ) : (
              <div className="w-48 h-48 mx-auto bg-gray-100 rounded-lg flex items-center justify-center mb-4">
                <LoadingSpinner />
              </div>
            )}
            
            <p className="text-sm text-gray-600">
              Scan this QR code with your authenticator app
            </p>
          </div>

          {/* Manual Setup */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-medium text-gray-900 mb-2">Can't scan the QR code?</h3>
            <p className="text-sm text-gray-600 mb-3">
              Enter this code manually in your authenticator app:
            </p>
            
            <div className="flex items-center space-x-2">
              <code className="flex-1 bg-white px-3 py-2 border rounded font-mono text-sm">
                {showSecret ? setupData?.manualEntryCode : '••••••••••••••••••••••••••••••••'}
              </code>
              <button
                onClick={() => setShowSecret(!showSecret)}
                className="p-2 text-gray-500 hover:text-gray-700"
                title={showSecret ? 'Hide' : 'Show'}
              >
                {showSecret ? <EyeSlashIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
              </button>
              <button
                onClick={() => copyToClipboard(setupData?.manualEntryCode || '')}
                className="p-2 text-gray-500 hover:text-gray-700"
                title="Copy to clipboard"
              >
                <ClipboardDocumentIcon className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="flex space-x-3">
            <button
              onClick={() => setCurrentStep('method')}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => setCurrentStep('verify')}
              disabled={!setupData}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              Continue
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const renderVerification = () => (
    <div className="space-y-6">
      <div className="text-center">
        <KeyIcon className="mx-auto h-12 w-12 text-blue-600 mb-4" />
        <h2 className="text-2xl font-bold text-gray-900">Verify Your Setup</h2>
        <p className="text-gray-600 mt-2">
          Enter the 6-digit code from your authenticator app to complete setup.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label htmlFor="verification-code" className="block text-sm font-medium text-gray-700 mb-2">
            Verification Code
          </label>
          <input
            type="text"
            id="verification-code"
            value={verificationCode}
            onChange={handleCodeInput}
            placeholder="000000"
            className="w-full px-4 py-3 text-center text-2xl font-mono border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            maxLength={6}
            autoComplete="one-time-code"
          />
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex">
              <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
              <div className="ml-3">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            </div>
          </div>
        )}

        <div className="flex space-x-3">
          <button
            onClick={() => setCurrentStep('setup')}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
          >
            Back
          </button>
          <button
            onClick={handleVerifyCode}
            disabled={verificationCode.length !== 6 || verifyLoading}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center"
          >
            {verifyLoading ? (
              <>
                <LoadingSpinner size="small" />
                <span className="ml-2">Verifying...</span>
              </>
            ) : (
              'Verify & Enable'
            )}
          </button>
        </div>
      </div>
    </div>
  );

  const renderBackupCodes = () => (
    <div className="space-y-6">
      <div className="text-center">
        <CheckCircleIcon className="mx-auto h-12 w-12 text-green-600 mb-4" />
        <h2 className="text-2xl font-bold text-gray-900">MFA Setup Complete!</h2>
        <p className="text-gray-600 mt-2">
          Save these backup codes in a secure place. You can use them if you lose access to your authenticator app.
        </p>
      </div>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex">
          <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800">Important</h3>
            <p className="text-sm text-yellow-700 mt-1">
              Each backup code can only be used once. Generate new codes if you run out.
            </p>
          </div>
        </div>
      </div>

      <div className="bg-white border-2 border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium text-gray-900">Your Backup Codes</h3>
          <button
            onClick={() => copyToClipboard(backupCodes.join('\n'))}
            className="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-800"
          >
            <ClipboardDocumentIcon className="h-4 w-4" />
            <span>Copy All</span>
          </button>
        </div>
        
        <div className="grid grid-cols-2 gap-2 font-mono text-sm">
          {backupCodes.map((code, index) => (
            <div key={index} className="bg-gray-50 p-2 rounded text-center">
              {code}
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <input
          type="checkbox"
          id="saved-codes"
          checked={savedCodes}
          onChange={(e) => setSavedCodes(e.target.checked)}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
        <label htmlFor="saved-codes" className="text-sm text-gray-700">
          I have saved these backup codes in a secure location
        </label>
      </div>

      <button
        onClick={handleFinishSetup}
        disabled={!savedCodes}
        className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
      >
        Complete Setup
      </button>
    </div>
  );

  if (loading) {
    return (
      <div className="text-center py-8">
        <LoadingSpinner size="large" />
        <p className="mt-4 text-gray-600">Loading MFA configuration...</p>
      </div>
    );
  }

  if (config?.status === MFAStatus.ENABLED) {
    return (
      <div className="text-center py-8">
        <CheckCircleIcon className="mx-auto h-12 w-12 text-green-600 mb-4" />
        <h2 className="text-xl font-bold text-gray-900">MFA is Already Enabled</h2>
        <p className="text-gray-600 mt-2">
          Your account is already protected with multi-factor authentication.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto">
      {currentStep === 'method' && renderMethodSelection()}
      {currentStep === 'setup' && renderTOTPSetup()}
      {currentStep === 'verify' && renderVerification()}
      {currentStep === 'backup' && renderBackupCodes()}
    </div>
  );
}
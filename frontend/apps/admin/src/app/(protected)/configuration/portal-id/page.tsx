'use client';

import { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { 
  Settings, 
  Save, 
  RefreshCw, 
  AlertCircle,
  CheckCircle2,
  Eye,
  Info,
  BarChart3,
  Key
} from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';

// Types
interface PortalIdPattern {
  value: string;
  name: string;
  description: string;
  example: string;
  recommended: boolean;
}

interface PortalIdConfig {
  id?: string;
  tenant_id: string;
  pattern: string;
  length: number;
  prefix: string;
  suffix: string;
  exclude_ambiguous: boolean;
  custom_charset: string;
  max_combinations?: number;
  example?: string;
  created_at?: string;
  updated_at?: string;
}

interface PortalIdStats {
  total_generated: number;
  total_assigned: number;
  total_active: number;
  pattern_breakdown: Record<string, number>;
}

// Mock data (replace with real API calls)
const mockPatterns: Record<string, PortalIdPattern> = {
  alphanumeric_clean: {
    value: 'alphanumeric_clean',
    name: 'Alphanumeric Clean',
    description: 'A-Z and 2-9 (excludes confusing characters like 0, O, I, 1)',
    example: 'ABC23XYZ',
    recommended: true
  },
  alphanumeric: {
    value: 'alphanumeric',
    name: 'Alphanumeric Full',
    description: 'A-Z and 0-9 (includes all characters)',
    example: 'ABC01XYZ',
    recommended: false
  },
  numeric: {
    value: 'numeric',
    name: 'Numeric Only',
    description: 'Numbers only (0-9)',
    example: '12345678',
    recommended: false
  },
  timestamp_based: {
    value: 'timestamp_based',
    name: 'Timestamp Based',
    description: 'Timestamp + random characters (legacy format)',
    example: 'PRT-1704067200-ABC123',
    recommended: false
  },
  custom: {
    value: 'custom',
    name: 'Custom Character Set',
    description: 'Use your own character set',
    example: 'CUSTOM123',
    recommended: false
  }
};

const mockCurrentConfig: PortalIdConfig = {
  tenant_id: 'tenant-123',
  pattern: 'alphanumeric_clean',
  length: 8,
  prefix: 'CUST-',
  suffix: '',
  exclude_ambiguous: true,
  custom_charset: '',
  max_combinations: 45697536,
  example: 'CUST-ABC23XYZ',
  updated_at: '2024-01-25T10:30:00Z'
};

const mockStats: PortalIdStats = {
  total_generated: 1247,
  total_assigned: 1108,
  total_active: 1095,
  pattern_breakdown: {
    'alphanumeric_clean': 1247
  }
};

export default function PortalIdConfigurationPage() {
  const [config, setConfig] = useState<PortalIdConfig>(mockCurrentConfig);
  const [patterns] = useState(mockPatterns);
  const [stats] = useState(mockStats);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [previewId, setPreviewId] = useState('');

  // Generate preview ID when config changes
  useEffect(() => {
    if (config) {
      const pattern = patterns[config.pattern];
      if (pattern) {
        // Simple preview generation (in real app, call API)
        let preview = config.prefix;
        if (config.pattern === 'timestamp_based') {
          preview += `${Date.now()}-ABC123`;
        } else {
          const chars = config.pattern === 'numeric' ? '2345678' : 'A2B3C4';
          preview += chars.substring(0, Math.max(1, config.length - config.prefix.length));
        }
        preview += config.suffix;
        setPreviewId(preview);
      }
    }
  }, [config, patterns]);

  const handleConfigChange = (field: keyof PortalIdConfig, value: any) => {
    setConfig(prev => ({ ...prev, [field]: value }));
    setIsDirty(true);
    setErrors(prev => ({ ...prev, [field]: '' })); // Clear field error
  };

  const validateConfig = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (config.length < 4) {
      newErrors.length = 'Length must be at least 4 characters';
    }
    if (config.length > 50) {
      newErrors.length = 'Length must not exceed 50 characters';
    }
    
    if (config.prefix.length + config.suffix.length >= config.length) {
      newErrors.prefix = 'Prefix + suffix length must be less than total length';
    }

    if (config.pattern === 'custom' && !config.custom_charset.trim()) {
      newErrors.custom_charset = 'Custom character set is required for custom pattern';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validateConfig()) return;

    setIsSaving(true);
    try {
      // TODO: Call actual API
      await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate API call
      setIsDirty(false);
      console.log('Configuration saved:', config);
    } catch (error) {
      console.error('Failed to save configuration:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    setConfig(mockCurrentConfig);
    setIsDirty(false);
    setErrors({});
  };

  const generateTestIds = async () => {
    setIsLoading(true);
    try {
      // TODO: Call actual API to generate test Portal IDs
      await new Promise(resolve => setTimeout(resolve, 1000));
      console.log('Generated test Portal IDs');
    } catch (error) {
      console.error('Failed to generate test Portal IDs:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const currentPattern = patterns[config.pattern];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <Key className="h-8 w-8 text-gray-600 mr-3" />
              <div>
                <h1 className="text-2xl font-semibold text-gray-900">Portal ID Configuration</h1>
                <p className="mt-1 text-sm text-gray-600">
                  Configure how Portal IDs are generated for your customers
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              {isDirty && (
                <div className="flex items-center text-amber-600">
                  <div className="h-2 w-2 bg-amber-400 rounded-full mr-2"></div>
                  <span className="text-sm font-medium">Unsaved changes</span>
                </div>
              )}
              <Button 
                variant="outline" 
                onClick={handleReset} 
                disabled={!isDirty}
              >
                Reset
              </Button>
              <Button 
                onClick={handleSave} 
                disabled={!isDirty || isSaving}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <Save className="mr-2 h-4 w-4" />
                {isSaving ? 'Saving...' : 'Save Configuration'}
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Configuration */}
          <div className="lg:col-span-2 space-y-6">
            {/* Pattern Selection */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Settings className="mr-2 h-5 w-5" />
                  Generation Pattern
                </CardTitle>
                <CardDescription>
                  Choose how Portal IDs should be generated for your customers
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="pattern">Pattern Type</Label>
                  <Select 
                    value={config.pattern} 
                    onValueChange={(value) => handleConfigChange('pattern', value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select a pattern" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.values(patterns).map((pattern) => (
                        <SelectItem key={pattern.value} value={pattern.value}>
                          <div className="flex items-center justify-between w-full">
                            <span>{pattern.name}</span>
                            {pattern.recommended && (
                              <Badge variant="secondary" className="ml-2">Recommended</Badge>
                            )}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {currentPattern && (
                    <p className="text-sm text-gray-600 mt-1">
                      {currentPattern.description}
                    </p>
                  )}
                </div>

                {/* Pattern-specific settings */}
                {config.pattern === 'custom' && (
                  <div>
                    <Label htmlFor="custom_charset">Custom Character Set</Label>
                    <Input
                      id="custom_charset"
                      value={config.custom_charset}
                      onChange={(e) => handleConfigChange('custom_charset', e.target.value)}
                      placeholder="Enter characters to use (e.g., ABCDEFG123456)"
                      className={errors.custom_charset ? 'border-red-500' : ''}
                    />
                    {errors.custom_charset && (
                      <p className="text-sm text-red-600 mt-1">{errors.custom_charset}</p>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Format Configuration */}
            <Card>
              <CardHeader>
                <CardTitle>Format Configuration</CardTitle>
                <CardDescription>
                  Customize the format of generated Portal IDs
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="prefix">Prefix</Label>
                    <Input
                      id="prefix"
                      value={config.prefix}
                      onChange={(e) => handleConfigChange('prefix', e.target.value)}
                      placeholder="e.g., CUST-"
                      className={errors.prefix ? 'border-red-500' : ''}
                    />
                    {errors.prefix && (
                      <p className="text-sm text-red-600 mt-1">{errors.prefix}</p>
                    )}
                  </div>
                  <div>
                    <Label htmlFor="length">Total Length</Label>
                    <Input
                      id="length"
                      type="number"
                      min="4"
                      max="50"
                      value={config.length}
                      onChange={(e) => handleConfigChange('length', parseInt(e.target.value) || 4)}
                      className={errors.length ? 'border-red-500' : ''}
                    />
                    {errors.length && (
                      <p className="text-sm text-red-600 mt-1">{errors.length}</p>
                    )}
                  </div>
                  <div>
                    <Label htmlFor="suffix">Suffix</Label>
                    <Input
                      id="suffix"
                      value={config.suffix}
                      onChange={(e) => handleConfigChange('suffix', e.target.value)}
                      placeholder="e.g., -2024"
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="exclude_ambiguous"
                    checked={config.exclude_ambiguous}
                    onCheckedChange={(checked) => handleConfigChange('exclude_ambiguous', checked)}
                    disabled={config.pattern === 'custom'}
                  />
                  <Label htmlFor="exclude_ambiguous" className="text-sm">
                    Exclude ambiguous characters (0, O, I, 1)
                  </Label>
                </div>
              </CardContent>
            </Card>

            {/* Test Generation */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Eye className="mr-2 h-5 w-5" />
                  Test Generation
                </CardTitle>
                <CardDescription>
                  Generate sample Portal IDs to test your configuration
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center space-x-4">
                  <Button 
                    variant="outline" 
                    onClick={generateTestIds}
                    disabled={isLoading}
                  >
                    <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                    Generate Test IDs
                  </Button>
                  <div className="text-sm text-gray-600">
                    Preview: <code className="bg-gray-100 px-2 py-1 rounded">{previewId}</code>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Current Statistics */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <BarChart3 className="mr-2 h-5 w-5" />
                  Current Statistics
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Total Generated:</span>
                  <span className="text-sm font-medium">{stats.total_generated.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Assigned:</span>
                  <span className="text-sm font-medium">{stats.total_assigned.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Active:</span>
                  <span className="text-sm font-medium">{stats.total_active.toLocaleString()}</span>
                </div>
                <Separator />
                <div className="text-xs text-gray-500">
                  Last updated: {new Date(config.updated_at || '').toLocaleString()}
                </div>
              </CardContent>
            </Card>

            {/* Configuration Info */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Info className="mr-2 h-5 w-5" />
                  Configuration Info
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <div className="text-sm text-gray-600">Max Combinations:</div>
                  <div className="text-lg font-mono">
                    {config.max_combinations?.toLocaleString() || 'Calculating...'}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Pattern:</div>
                  <div className="text-sm font-medium">{currentPattern?.name}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Format:</div>
                  <div className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                    {config.prefix}[{config.length - config.prefix.length - config.suffix.length} chars]{config.suffix}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Warnings */}
            {config.max_combinations && config.max_combinations < 10000 && (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Warning: Current configuration provides only {config.max_combinations?.toLocaleString()} unique combinations. 
                  Consider increasing length or changing pattern.
                </AlertDescription>
              </Alert>
            )}

            {currentPattern?.recommended === false && (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  The selected pattern is not recommended for production use. 
                  Consider using "Alphanumeric Clean" for better user experience.
                </AlertDescription>
              </Alert>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
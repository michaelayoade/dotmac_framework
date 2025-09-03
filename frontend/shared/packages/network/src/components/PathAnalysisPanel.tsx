/**
 * Path Analysis Panel
 * Network path analysis and visualization component
 */

import React, { useState, useEffect, useMemo } from 'react';
import { Card, Button, Badge } from '@dotmac/primitives';
import {
  Navigation,
  MapPin,
  Clock,
  Zap,
  AlertTriangle,
  CheckCircle,
  ArrowRight,
  Activity,
  BarChart3,
  Repeat,
  Play,
  Square,
} from 'lucide-react';

export interface NetworkHop {
  id: string;
  address: string;
  hostname?: string;
  rtt: number; // Round trip time in ms
  packetLoss: number; // Percentage
  status: 'reachable' | 'timeout' | 'unreachable';
  asn?: string; // Autonomous System Number
  location?: string;
  provider?: string;
}

export interface PathAnalysisResult {
  id: string;
  source: string;
  destination: string;
  totalHops: number;
  totalRtt: number;
  averageRtt: number;
  packetLoss: number;
  status: 'completed' | 'failed' | 'running';
  timestamp: number;
  hops: NetworkHop[];
  mtu?: number; // Maximum Transmission Unit
  protocol: 'tcp' | 'udp' | 'icmp';
}

export interface PathAnalysisConfig {
  destination: string;
  maxHops: number;
  timeout: number;
  protocol: 'tcp' | 'udp' | 'icmp';
  port?: number;
  packetSize?: number;
  probeCount?: number;
}

export interface PathAnalysisPanelProps {
  results: PathAnalysisResult[];
  onStartAnalysis: (config: PathAnalysisConfig) => void;
  onStopAnalysis: () => void;
  isRunning?: boolean;
  className?: string;
}

export const PathAnalysisPanel: React.FC<PathAnalysisPanelProps> = ({
  results = [],
  onStartAnalysis,
  onStopAnalysis,
  isRunning = false,
  className,
}) => {
  const [config, setConfig] = useState<PathAnalysisConfig>({
    destination: '',
    maxHops: 30,
    timeout: 5000,
    protocol: 'icmp',
    packetSize: 64,
    probeCount: 3,
  });
  const [selectedResult, setSelectedResult] = useState<PathAnalysisResult | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Get latest result if available
  const latestResult = useMemo(() => {
    return results.length > 0 ? results[0] : null;
  }, [results]);

  // Calculate path statistics
  const pathStats = useMemo(() => {
    if (!selectedResult && !latestResult) return null;

    const result = selectedResult || latestResult!;
    const reachableHops = result.hops.filter((h) => h.status === 'reachable');
    const totalRtt = reachableHops.reduce((sum, hop) => sum + hop.rtt, 0);
    const avgPacketLoss =
      result.hops.reduce((sum, hop) => sum + hop.packetLoss, 0) / result.hops.length;

    return {
      reachableHops: reachableHops.length,
      totalHops: result.totalHops,
      avgRtt: totalRtt / reachableHops.length || 0,
      maxRtt: Math.max(...reachableHops.map((h) => h.rtt)) || 0,
      minRtt: Math.min(...reachableHops.map((h) => h.rtt)) || 0,
      avgPacketLoss: avgPacketLoss || 0,
      qualityScore: Math.max(
        0,
        100 - (avgPacketLoss * 2 + (totalRtt / reachableHops.length || 0) / 10)
      ),
    };
  }, [selectedResult, latestResult]);

  const handleStartAnalysis = () => {
    if (config.destination) {
      onStartAnalysis(config);
    }
  };

  const getHopStatusIcon = (status: string) => {
    switch (status) {
      case 'reachable':
        return <CheckCircle className='w-4 h-4 text-green-500' />;
      case 'timeout':
        return <Clock className='w-4 h-4 text-yellow-500' />;
      case 'unreachable':
        return <AlertTriangle className='w-4 h-4 text-red-500' />;
      default:
        return <Activity className='w-4 h-4 text-gray-400' />;
    }
  };

  const getQualityColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const currentResult = selectedResult || latestResult;

  return (
    <div className={`space-y-6 ${className || ''}`}>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div className='flex items-center space-x-2'>
          <Navigation className='w-6 h-6 text-blue-500' />
          <h2 className='text-2xl font-bold text-gray-900'>Path Analysis</h2>
        </div>

        <div className='flex items-center space-x-2'>
          {results.length > 1 && (
            <select
              value={selectedResult?.id || ''}
              onChange={(e) => {
                const result = results.find((r) => r.id === e.target.value);
                setSelectedResult(result || null);
              }}
              className='px-3 py-1 border border-gray-300 rounded text-sm'
            >
              <option value=''>Latest Result</option>
              {results.map((result, index) => (
                <option key={result.id} value={result.id}>
                  {result.destination} ({new Date(result.timestamp).toLocaleTimeString()})
                </option>
              ))}
            </select>
          )}

          <Button variant='outline' size='sm' onClick={() => setShowAdvanced(!showAdvanced)}>
            Advanced
          </Button>
        </div>
      </div>

      {/* Configuration Panel */}
      <Card className='p-4'>
        <div className='space-y-4'>
          <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>Destination</label>
              <input
                type='text'
                value={config.destination}
                onChange={(e) => setConfig({ ...config, destination: e.target.value })}
                placeholder='Enter IP address or hostname'
                className='w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                disabled={isRunning}
              />
            </div>

            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>Protocol</label>
              <select
                value={config.protocol}
                onChange={(e) => setConfig({ ...config, protocol: e.target.value as any })}
                className='w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                disabled={isRunning}
              >
                <option value='icmp'>ICMP</option>
                <option value='tcp'>TCP</option>
                <option value='udp'>UDP</option>
              </select>
            </div>
          </div>

          {showAdvanced && (
            <div className='grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-gray-200'>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Max Hops</label>
                <input
                  type='number'
                  value={config.maxHops}
                  onChange={(e) => setConfig({ ...config, maxHops: parseInt(e.target.value) })}
                  className='w-full px-3 py-2 border border-gray-300 rounded text-sm'
                  disabled={isRunning}
                  min='1'
                  max='64'
                />
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Timeout (ms)</label>
                <input
                  type='number'
                  value={config.timeout}
                  onChange={(e) => setConfig({ ...config, timeout: parseInt(e.target.value) })}
                  className='w-full px-3 py-2 border border-gray-300 rounded text-sm'
                  disabled={isRunning}
                  min='1000'
                  max='30000'
                />
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Packet Size</label>
                <input
                  type='number'
                  value={config.packetSize}
                  onChange={(e) => setConfig({ ...config, packetSize: parseInt(e.target.value) })}
                  className='w-full px-3 py-2 border border-gray-300 rounded text-sm'
                  disabled={isRunning}
                  min='32'
                  max='1472'
                />
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Probes</label>
                <input
                  type='number'
                  value={config.probeCount}
                  onChange={(e) => setConfig({ ...config, probeCount: parseInt(e.target.value) })}
                  className='w-full px-3 py-2 border border-gray-300 rounded text-sm'
                  disabled={isRunning}
                  min='1'
                  max='10'
                />
              </div>
            </div>
          )}

          <div className='flex items-center justify-between'>
            <div className='flex items-center space-x-2'>
              {isRunning ? (
                <Button onClick={onStopAnalysis} variant='destructive'>
                  <Square className='w-4 h-4 mr-2' />
                  Stop Analysis
                </Button>
              ) : (
                <Button onClick={handleStartAnalysis} disabled={!config.destination}>
                  <Play className='w-4 h-4 mr-2' />
                  Start Analysis
                </Button>
              )}
            </div>

            {isRunning && (
              <div className='flex items-center text-sm text-blue-600'>
                <Activity className='w-4 h-4 mr-1 animate-spin' />
                Analysis in progress...
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Results Summary */}
      {pathStats && currentResult && (
        <div className='grid grid-cols-1 md:grid-cols-4 gap-4'>
          <Card className='p-4'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='text-sm font-medium text-gray-500'>Total Hops</p>
                <p className='text-2xl font-bold text-gray-900'>{pathStats.totalHops}</p>
              </div>
              <MapPin className='w-8 h-8 text-blue-500' />
            </div>
          </Card>

          <Card className='p-4'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='text-sm font-medium text-gray-500'>Avg RTT</p>
                <p className='text-2xl font-bold text-gray-900'>{pathStats.avgRtt.toFixed(1)}ms</p>
              </div>
              <Clock className='w-8 h-8 text-green-500' />
            </div>
          </Card>

          <Card className='p-4'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='text-sm font-medium text-gray-500'>Packet Loss</p>
                <p className='text-2xl font-bold text-gray-900'>
                  {pathStats.avgPacketLoss.toFixed(1)}%
                </p>
              </div>
              <AlertTriangle className='w-8 h-8 text-yellow-500' />
            </div>
          </Card>

          <Card className='p-4'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='text-sm font-medium text-gray-500'>Quality Score</p>
                <p className={`text-2xl font-bold ${getQualityColor(pathStats.qualityScore)}`}>
                  {pathStats.qualityScore.toFixed(0)}/100
                </p>
              </div>
              <BarChart3 className='w-8 h-8 text-purple-500' />
            </div>
          </Card>
        </div>
      )}

      {/* Path Visualization */}
      {currentResult && (
        <Card className='p-6'>
          <div className='flex items-center justify-between mb-4'>
            <h3 className='text-lg font-medium text-gray-900'>
              Path to {currentResult.destination}
            </h3>
            <Badge variant={currentResult.status === 'completed' ? 'default' : 'destructive'}>
              {currentResult.status}
            </Badge>
          </div>

          <div className='space-y-3'>
            {currentResult.hops.map((hop, index) => (
              <div
                key={hop.id}
                className='flex items-center space-x-4 p-3 border rounded-lg hover:bg-gray-50'
              >
                <div className='flex items-center space-x-2 min-w-0 flex-1'>
                  <span className='text-sm font-medium text-gray-500 w-8'>{index + 1}</span>

                  {getHopStatusIcon(hop.status)}

                  <div className='min-w-0 flex-1'>
                    <div className='flex items-center space-x-2'>
                      <code className='text-sm font-mono text-gray-900'>{hop.address}</code>
                      {hop.hostname && (
                        <span className='text-sm text-gray-500'>({hop.hostname})</span>
                      )}
                    </div>

                    {(hop.location || hop.provider) && (
                      <div className='flex items-center space-x-2 text-xs text-gray-500 mt-1'>
                        {hop.location && (
                          <span className='flex items-center space-x-1'>
                            <MapPin className='w-3 h-3' />
                            <span>{hop.location}</span>
                          </span>
                        )}
                        {hop.provider && <span>{hop.provider}</span>}
                        {hop.asn && <span>AS{hop.asn}</span>}
                      </div>
                    )}
                  </div>
                </div>

                <div className='flex items-center space-x-4 text-sm'>
                  {hop.status === 'reachable' ? (
                    <>
                      <div className='text-right'>
                        <div className='font-medium text-gray-900'>{hop.rtt.toFixed(1)}ms</div>
                        <div className='text-xs text-gray-500'>RTT</div>
                      </div>

                      {hop.packetLoss > 0 && (
                        <div className='text-right'>
                          <div className='font-medium text-red-600'>
                            {hop.packetLoss.toFixed(1)}%
                          </div>
                          <div className='text-xs text-gray-500'>Loss</div>
                        </div>
                      )}
                    </>
                  ) : (
                    <span className='text-gray-500 capitalize'>{hop.status}</span>
                  )}
                </div>

                {index < currentResult.hops.length - 1 && (
                  <ArrowRight className='w-4 h-4 text-gray-300' />
                )}
              </div>
            ))}
          </div>

          <div className='mt-4 pt-4 border-t border-gray-200 text-sm text-gray-500'>
            Analysis completed at {new Date(currentResult.timestamp).toLocaleString()}
            {currentResult.mtu && <span className='ml-4'>MTU: {currentResult.mtu} bytes</span>}
          </div>
        </Card>
      )}
    </div>
  );
};

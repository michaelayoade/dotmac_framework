/**
 * Universal Report Generator
 * Leverages @dotmac/primitives charts and @dotmac/data-tables export functionality
 */

import React, { useMemo, useCallback, useRef } from 'react';
import { motion } from 'framer-motion';
import { Download, FileText, BarChart3, Table, Calendar, Share2 } from 'lucide-react';
import { UniversalChart } from '@dotmac/primitives';
import { UniversalDataTable } from '@dotmac/primitives';
import { exportData } from '@dotmac/data-tables';
import { Button, Card } from '@dotmac/primitives';
import { useReportData } from '../hooks/useReportData';
import { useReportExport } from '../hooks/useReportExport';
import type { Report, ReportResult, ExportFormat, PortalVariant } from '../types';
import { cn } from '../utils/cn';

interface UniversalReportGeneratorProps {
  report: Report;
  variant?: PortalVariant;
  className?: string;
  showHeader?: boolean;
  showExport?: boolean;
  showSchedule?: boolean;
  autoRefresh?: boolean;
  onReportGenerated?: (result: ReportResult) => void;
  onExportComplete?: (format: ExportFormat, url: string) => void;
  onScheduleUpdate?: (schedule: any) => void;
}

export const UniversalReportGenerator: React.FC<UniversalReportGeneratorProps> = ({
  report,
  variant,
  className,
  showHeader = true,
  showExport = true,
  showSchedule = false,
  autoRefresh = false,
  onReportGenerated,
  onExportComplete,
  onScheduleUpdate
}) => {
  const reportRef = useRef<HTMLDivElement>(null);

  // Leverage existing @dotmac/headless data fetching
  const {
    data,
    loading,
    error,
    refresh,
    executionTime
  } = useReportData(report.config.dataSource);

  // Leverage existing @dotmac/data-tables export functionality
  const {
    exportReport,
    exporting,
    exportFormats
  } = useReportExport();

  // Process data based on report configuration
  const processedData = useMemo(() => {
    if (!data) return [];

    let processed = data;

    // Apply filters
    report.config.filters.forEach(filter => {
      processed = processed.filter(row => {
        const value = row[filter.field];

        switch (filter.operator) {
          case 'eq':
            return value === filter.value;
          case 'ne':
            return value !== filter.value;
          case 'gt':
            return value > filter.value;
          case 'gte':
            return value >= filter.value;
          case 'lt':
            return value < filter.value;
          case 'lte':
            return value <= filter.value;
          case 'contains':
            return String(value).toLowerCase().includes(String(filter.value).toLowerCase());
          case 'in':
            return filter.values?.includes(value);
          case 'between':
            return value >= filter.value[0] && value <= filter.value[1];
          default:
            return true;
        }
      });
    });

    // Apply sorting
    if (report.config.sorting?.length) {
      processed = processed.sort((a, b) => {
        for (const sort of report.config.sorting!) {
          const aVal = a[sort.field];
          const bVal = b[sort.field];

          if (aVal < bVal) return sort.direction === 'asc' ? -1 : 1;
          if (aVal > bVal) return sort.direction === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }

    // Apply aggregation if needed
    if (report.config.aggregation?.length) {
      // Group by grouping fields
      if (report.config.grouping) {
        const grouped = processed.reduce((acc, row) => {
          const key = report.config.grouping!.fields
            .map(field => row[field])
            .join('|');

          if (!acc[key]) {
            acc[key] = [];
          }
          acc[key].push(row);
          return acc;
        }, {} as Record<string, any[]>);

        // Calculate aggregations for each group
        processed = Object.entries(grouped).map(([key, group]) => {
          const result: any = {};

          // Include grouping fields
          report.config.grouping!.fields.forEach((field, index) => {
            result[field] = key.split('|')[index];
          });

          // Calculate aggregations
          report.config.aggregation!.forEach(agg => {
            const values = (group as any[]).map((row: any) => row[agg.field]).filter((v: any) => v != null);

            switch (agg.operation) {
              case 'sum':
                result[agg.label || `${agg.field}_sum`] = values.reduce((sum: number, val: any) => sum + Number(val), 0);
                break;
              case 'avg':
                result[agg.label || `${agg.field}_avg`] = values.reduce((sum: number, val: any) => sum + Number(val), 0) / values.length;
                break;
              case 'count':
                result[agg.label || `${agg.field}_count`] = values.length;
                break;
              case 'min':
                result[agg.label || `${agg.field}_min`] = Math.min(...values.map(Number));
                break;
              case 'max':
                result[agg.label || `${agg.field}_max`] = Math.max(...values.map(Number));
                break;
              case 'countDistinct':
                result[agg.label || `${agg.field}_distinct`] = new Set(values).size;
                break;
            }
          });

          return result;
        });
      }
    }

    return processed;
  }, [data, report.config]);

  // Handle export using existing @dotmac/data-tables functionality
  const handleExport = useCallback(async (format: ExportFormat) => {
    if (!processedData.length) return;

    try {
      const filename = `${report.title.toLowerCase().replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}`;

      if (format === 'png' && reportRef.current) {
        // Use html2canvas for visual exports
        try {
          const html2canvas = await import('html2canvas' as any);
          const canvas = await (html2canvas as any).default(reportRef.current);
          const link = document.createElement('a');
          link.download = `${filename}.png`;
          link.href = canvas.toDataURL();
          link.click();
          onExportComplete?.(format, link.href);
          return;
        } catch (error) {
          console.error('PNG export failed:', error);
          return;
        }
      }

      // Use existing export functionality from @dotmac/data-tables
      await exportData(
        format as any,
        processedData,
        {
          filename,
          includeHeaders: true,
          formats: [format === 'html' || format === 'png' ? 'pdf' : format] as ('pdf' | 'csv' | 'xlsx' | 'json')[],
          ...(report.config.visualization.table?.columns && {
            customFields: report.config.visualization.table.columns.map(col => ({
              key: col.key,
              label: col.title,
              accessor: (row: any) => col.formatter ? col.formatter(row[col.key], row) : row[col.key]
            }))
          })
        },
        {
          portal: variant || report.portal,
          title: report.title,
          orientation: 'landscape'
        }
      );

      onExportComplete?.(format, '');
    } catch (error) {
      console.error('Export failed:', error);
    }
  }, [processedData, report, variant, onExportComplete]);

  // Generate report result
  const reportResult: ReportResult = useMemo(() => ({
    data: processedData,
    metadata: {
      totalRows: processedData.length,
      columns: processedData.length > 0 ? Object.keys(processedData[0]) : [],
      executionTime: executionTime || 0,
      dataSource: report.config.dataSource.endpoint || 'static',
      generatedAt: new Date()
    }
  }), [processedData, executionTime, report.config.dataSource.endpoint]);

  // Notify when report is generated
  React.useEffect(() => {
    if (reportResult.data.length > 0) {
      onReportGenerated?.(reportResult);
    }
  }, [reportResult, onReportGenerated]);

  // Render visualization based on configuration
  const renderVisualization = () => {
    const { visualization } = report.config;

    switch (visualization.type) {
      case 'chart':
        return (
          <div className="space-y-6">
            {visualization.charts?.map((chartConfig) => (
              <motion.div
                key={chartConfig.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  "w-full",
                  chartConfig.size === 'small' && "h-64",
                  chartConfig.size === 'medium' && "h-80",
                  chartConfig.size === 'large' && "h-96",
                  chartConfig.size === 'full' && "h-[500px]"
                )}
              >
                <UniversalChart
                  type={chartConfig.type}
                  data={chartConfig.data}
                  title={chartConfig.title}
                  variant={variant || report.portal}
                  series={chartConfig.series as any}
                  showLegend
                  showTooltip
                  showGrid
                />
              </motion.div>
            ))}
          </div>
        );

      case 'table':
        return (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="w-full"
          >
            <UniversalDataTable
              data={processedData}
              columns={visualization.table?.columns as any}
              variant="default"
              exportable
            />
          </motion.div>
        );

      case 'mixed':
        return (
          <div className="space-y-6">
            {/* Charts */}
            {visualization.charts?.map((chartConfig) => (
              <motion.div
                key={chartConfig.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full h-80"
              >
                <UniversalChart
                  type={chartConfig.type}
                  data={chartConfig.data}
                  title={chartConfig.title}
                  variant={variant || report.portal}
                  series={chartConfig.series as any}
                  showLegend
                  showTooltip
                />
              </motion.div>
            ))}

            {/* Table */}
            {visualization.table && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="w-full"
              >
                <UniversalDataTable
                  data={processedData}
                  columns={visualization.table.columns as any}
                  variant="default"
                  exportable
                />
              </motion.div>
            )}
          </div>
        );

      default:
        return (
          <div className="text-center py-8 text-gray-500">
            <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No visualization configured</p>
          </div>
        );
    }
  };

  if (error) {
    return (
      <Card className={cn("p-6", className)}>
        <div className="text-center py-8 text-red-500">
          <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p className="font-medium">Report Generation Failed</p>
          <p className="text-sm text-gray-500 mt-2">{error}</p>
          <Button
            variant="outline"
            onClick={refresh}
            className="mt-4"
          >
            Try Again
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <Card className={cn("overflow-hidden", className)}>
      {showHeader && (
        <div className="border-b border-gray-200 bg-gray-50 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{report.title}</h3>
              {report.description && (
                <p className="text-sm text-gray-600 mt-1">{report.description}</p>
              )}
            </div>

            <div className="flex items-center space-x-2">
              {autoRefresh && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={refresh}
                  disabled={loading}
                  className="text-gray-500"
                >
                  <BarChart3 className="h-4 w-4" />
                </Button>
              )}

              {showSchedule && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onScheduleUpdate?.(report.schedule)}
                  className="text-gray-500"
                >
                  <Calendar className="h-4 w-4" />
                </Button>
              )}

              {showExport && (
                <div className="flex items-center space-x-1">
                  {exportFormats.map((format) => (
                    <Button
                      key={format}
                      variant="ghost"
                      size="sm"
                      onClick={() => handleExport(format)}
                      disabled={loading || exporting}
                      className="text-gray-500"
                      title={`Export as ${format.toUpperCase()}`}
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                  ))}
                </div>
              )}

              <Button
                variant="ghost"
                size="sm"
                className="text-gray-500"
                title="Share Report"
              >
                <Share2 className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Report metadata */}
          <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
            <span>Records: {reportResult.metadata.totalRows.toLocaleString()}</span>
            <span>•</span>
            <span>Generated: {reportResult.metadata.generatedAt.toLocaleString()}</span>
            {reportResult.metadata.executionTime > 0 && (
              <>
                <span>•</span>
                <span>Execution: {reportResult.metadata.executionTime}ms</span>
              </>
            )}
          </div>
        </div>
      )}

      <div ref={reportRef} className="p-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Generating report...</span>
          </div>
        ) : (
          renderVisualization()
        )}
      </div>
    </Card>
  );
};

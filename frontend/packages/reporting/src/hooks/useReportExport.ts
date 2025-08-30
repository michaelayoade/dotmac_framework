/**
 * Report Export Hook
 * Leverages @dotmac/data-tables export functionality
 */

import { useState, useCallback } from 'react';
import { exportData } from '@dotmac/data-tables';
import type { ExportFormat, PortalVariant } from '../types';

interface UseReportExportReturn {
  exportReport: (
    format: ExportFormat,
    data: any[],
    options: {
      filename?: string;
      title?: string;
      portal?: PortalVariant;
      columns?: any[];
    }
  ) => Promise<void>;
  exporting: boolean;
  exportProgress: number;
  exportFormats: ExportFormat[];
}

export const useReportExport = (): UseReportExportReturn => {
  const [exporting, setExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);

  // Available export formats
  const exportFormats: ExportFormat[] = ['pdf', 'csv', 'xlsx', 'json', 'png', 'html'];

  const exportReport = useCallback(async (
    format: ExportFormat,
    data: any[],
    options: {
      filename?: string;
      title?: string;
      portal?: PortalVariant;
      columns?: any[];
    } = {}
  ): Promise<void> => {
    if (exporting) return;

    setExporting(true);
    setExportProgress(0);

    try {
      const { filename, title, portal = 'admin', columns } = options;

      // Generate filename if not provided
      const timestamp = new Date().toISOString().split('T')[0];
      const defaultFilename = title
        ? `${title.toLowerCase().replace(/\s+/g, '_')}_${timestamp}`
        : `report_${timestamp}`;
      const finalFilename = filename || defaultFilename;

      setExportProgress(25);

      // Handle different export formats
      switch (format) {
        case 'png':
          await exportAsImage(data, finalFilename, title);
          break;

        case 'html':
          await exportAsHTML(data, finalFilename, title, portal, columns);
          break;

        default:
          // Use existing @dotmac/data-tables export functionality
          await exportData(
            format as any,
            data,
            {
              filename: finalFilename,
              includeHeaders: true,
              formats: [format] as any,
              ...(columns && {
                customFields: columns.map(col => ({
                  key: col.key,
                  label: col.title,
                  accessor: (row: any) => col.formatter ? col.formatter(row[col.key], row) : row[col.key]
                }))
              })
            },
            {
              portal,
              title: title || 'Report',
              orientation: 'landscape',
              pageSize: 'A4'
            }
          );
          break;
      }

      setExportProgress(100);

      // Brief delay to show completion
      setTimeout(() => {
        setExportProgress(0);
        setExporting(false);
      }, 500);

    } catch (error) {
      console.error('Export failed:', error);
      setExporting(false);
      setExportProgress(0);
      throw error;
    }
  }, [exporting]);

  return {
    exportReport,
    exporting,
    exportProgress,
    exportFormats
  };
};

// Helper function for image export
const exportAsImage = async (data: any[], filename: string, title?: string): Promise<void> => {
  try {
    // Dynamic import to avoid bundle bloat
    const html2canvas = await import('html2canvas' as any);

    // Create a temporary container for the report
    const container = document.createElement('div');
    container.style.position = 'absolute';
    container.style.left = '-9999px';
    container.style.width = '1200px';
    container.style.padding = '20px';
    container.style.backgroundColor = 'white';
    container.style.fontFamily = 'system-ui, -apple-system, sans-serif';

    // Generate HTML content
    let html = '';

    if (title) {
      html += `<h1 style="color: #1f2937; margin-bottom: 20px; font-size: 24px;">${title}</h1>`;
    }

    html += `
      <div style="margin-bottom: 10px; color: #6b7280; font-size: 12px;">
        Generated on: ${new Date().toLocaleString()} | Records: ${data.length.toLocaleString()}
      </div>
    `;

    if (data.length > 0) {
      const headers = Object.keys(data[0]);
      html += '<table style="width: 100%; border-collapse: collapse; margin-top: 20px;">';

      // Headers
      html += '<thead><tr>';
      headers.forEach(header => {
        html += `<th style="border: 1px solid #d1d5db; padding: 8px; background-color: #f3f4f6; text-align: left; font-weight: 600;">${header}</th>`;
      });
      html += '</tr></thead>';

      // Data rows (limit to first 50 for image export)
      html += '<tbody>';
      data.slice(0, 50).forEach(row => {
        html += '<tr>';
        headers.forEach(header => {
          const value = row[header];
          html += `<td style="border: 1px solid #d1d5db; padding: 8px;">${value ?? ''}</td>`;
        });
        html += '</tr>';
      });
      html += '</tbody></table>';

      if (data.length > 50) {
        html += `<div style="margin-top: 10px; color: #6b7280; font-size: 12px;">... and ${data.length - 50} more records</div>`;
      }
    }

    container.innerHTML = html;
    document.body.appendChild(container);

    // Generate canvas
    const canvas = await html2canvas.default(container, {
      backgroundColor: 'white',
      scale: 2,
      width: 1200,
      height: container.scrollHeight
    });

    // Create download link
    const link = document.createElement('a');
    link.download = `${filename}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();

    // Cleanup
    document.body.removeChild(container);

  } catch (error) {
    console.error('Image export failed:', error);
    throw new Error('Image export failed. Please try PDF format instead.');
  }
};

// Helper function for HTML export
const exportAsHTML = async (
  data: any[],
  filename: string,
  title?: string,
  portal: PortalVariant = 'admin',
  columns?: any[]
): Promise<void> => {
  try {
    // Portal color schemes
    const portalColors = {
      admin: { primary: '#3b82f6', secondary: '#eff6ff' },
      customer: '#22c55e',
      reseller: '#a855f7',
      technician: '#f97316',
      management: '#ef4444'
    };

    const portalColor = portalColors[portal as keyof typeof portalColors];
    const primaryColor = (typeof portalColor === 'object' ? portalColor.primary : portalColor) || portalColors.admin.primary;

    let html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title || 'Report'}</title>
    <style>
        body {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #374151;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9fafb;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            border-left: 4px solid ${primaryColor};
        }
        .title {
            color: #1f2937;
            font-size: 28px;
            font-weight: 700;
            margin: 0 0 10px 0;
        }
        .meta {
            color: #6b7280;
            font-size: 14px;
            margin: 0;
        }
        .table-container {
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            background-color: ${primaryColor};
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
            font-size: 14px;
        }
        tr:nth-child(even) {
            background-color: #f9fafb;
        }
        .footer {
            margin-top: 30px;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            text-align: center;
            color: #6b7280;
            font-size: 12px;
        }
        @media print {
            body { background: white; }
            .header, .table-container, .footer { box-shadow: none; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">${title || 'Report'}</h1>
        <p class="meta">
            Generated on: ${new Date().toLocaleString()} |
            Total Records: ${data.length.toLocaleString()} |
            Portal: ${portal.charAt(0).toUpperCase() + portal.slice(1)}
        </p>
    </div>

    <div class="table-container">
        <table>
`;

    if (data.length > 0) {
      const headers = columns?.map(col => col.title) || Object.keys(data[0]);
      const keys = columns?.map(col => col.key) || Object.keys(data[0]);

      // Headers
      html += '<thead><tr>';
      headers.forEach(header => {
        html += `<th>${header}</th>`;
      });
      html += '</tr></thead>';

      // Data rows
      html += '<tbody>';
      data.forEach(row => {
        html += '<tr>';
        keys.forEach((key, index) => {
          let value = row[key];

          // Apply formatter if available
          if (columns?.[index]?.formatter) {
            value = columns[index].formatter(value, row);
          }

          html += `<td>${value ?? ''}</td>`;
        });
        html += '</tr>';
      });
      html += '</tbody>';
    }

    html += `
        </table>
    </div>

    <div class="footer">
        <p>This report was generated by DotMAC Framework • ${new Date().getFullYear()}</p>
    </div>
</body>
</html>`;

    // Create and download
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${filename}.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);

  } catch (error) {
    console.error('HTML export failed:', error);
    throw new Error('HTML export failed. Please try PDF format instead.');
  }
};

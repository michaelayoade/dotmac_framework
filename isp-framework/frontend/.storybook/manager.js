import { addons } from '@storybook/manager-api';
import { themes } from '@storybook/theming';

// Custom theme configuration
const customTheme = {
  ...themes.light,

  // Brand
  brandTitle: 'DotMac Design System',
  brandUrl: 'https://github.com/dotmac-framework',
  brandImage: undefined, // Add logo URL here if available
  brandTarget: '_self',

  // Colors
  colorPrimary: '#0066cc',
  colorSecondary: '#333333',

  // UI
  appBg: '#f8fafc',
  appContentBg: '#ffffff',
  appBorderColor: '#e2e8f0',
  appBorderRadius: 8,

  // Toolbar
  barTextColor: '#64748b',
  barSelectedColor: '#0066cc',
  barBg: '#ffffff',

  // Form
  inputBg: '#ffffff',
  inputBorder: '#e2e8f0',
  inputTextColor: '#1e293b',
  inputBorderRadius: 6,
};

// Configure Storybook manager
addons.setConfig({
  theme: customTheme,

  // Panel configuration
  panelPosition: 'bottom',
  selectedPanel: 'controls',

  // Sidebar configuration
  sidebar: {
    showRoots: true,
    collapsedRoots: ['other'],
    renderLabel: (item) => {
      // Custom labeling for better organization
      if (item.type === 'group') {
        return item.name.replace(/\//g, ' / ');
      }
      return item.name;
    },
  },

  // Toolbar configuration
  toolbar: {
    title: { hidden: false },
    zoom: { hidden: false },
    eject: { hidden: false },
    copy: { hidden: false },
    fullscreen: { hidden: false },
  },
});

// Custom CSS for manager UI
const style = document.createElement('style');
style.textContent = `
  /* Custom scrollbar */
  ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }
  
  ::-webkit-scrollbar-track {
    background: #f1f5f9;
    border-radius: 4px;
  }
  
  ::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 4px;
  }
  
  ::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
  }
  
  /* Sidebar improvements */
  .sidebar-container {
    border-right: 1px solid #e2e8f0;
  }
  
  /* Better focus styles */
  .sidebar-item:focus,
  button:focus,
  [role="button"]:focus {
    outline: 2px solid #0066cc;
    outline-offset: 2px;
  }
  
  /* Component status indicators */
  .sidebar-item[data-nodetype="component"]::before {
    content: "🧩";
    margin-right: 4px;
  }
  
  .sidebar-item[data-nodetype="story"]::before {
    content: "📄";
    margin-right: 4px;
  }
  
  /* Security status indicators */
  [data-security-tested="true"]::after {
    content: "🔒";
    margin-left: 4px;
    font-size: 12px;
  }
  
  [data-a11y-tested="true"]::after {
    content: "♿";
    margin-left: 4px;
    font-size: 12px;
  }
  
  /* Performance indicators */
  [data-performance="good"]::after {
    content: "⚡";
    margin-left: 4px;
    color: green;
  }
  
  [data-performance="warning"]::after {
    content: "⚠️";
    margin-left: 4px;
    color: orange;
  }
  
  [data-performance="poor"]::after {
    content: "🐌";
    margin-left: 4px;
    color: red;
  }
`;

document.head.appendChild(style);

/**
 * Design System Tokens
 * 
 * Comprehensive design tokens for the ISP management platform
 * Supports multiple themes, platforms, and accessibility requirements
 */

export interface ColorScale {
  50: string;
  100: string;
  200: string;
  300: string;
  400: string;
  500: string;
  600: string;
  700: string;
  800: string;
  900: string;
  950: string;
}

export interface SemanticColors {
  primary: ColorScale;
  secondary: ColorScale;
  accent: ColorScale;
  neutral: ColorScale;
  success: ColorScale;
  warning: ColorScale;
  error: ColorScale;
  info: ColorScale;
}

export interface ThemeColors extends SemanticColors {
  // Brand colors
  brand: {
    primary: string;
    secondary: string;
    accent: string;
  };
  
  // Surface colors
  surface: {
    background: string;
    backgroundSecondary: string;
    backgroundTertiary: string;
    card: string;
    cardSecondary: string;
    overlay: string;
    modal: string;
  };
  
  // Text colors
  text: {
    primary: string;
    secondary: string;
    tertiary: string;
    disabled: string;
    inverse: string;
    link: string;
    linkHover: string;
  };
  
  // Border colors
  border: {
    default: string;
    subtle: string;
    strong: string;
    interactive: string;
    focus: string;
    error: string;
    success: string;
    warning: string;
  };
  
  // ISP-specific colors
  network: {
    online: string;
    offline: string;
    maintenance: string;
    degraded: string;
  };
  
  service: {
    active: string;
    inactive: string;
    suspended: string;
    pending: string;
  };
  
  billing: {
    paid: string;
    unpaid: string;
    overdue: string;
    refunded: string;
  };
}

export interface Typography {
  fontFamily: {
    sans: string;
    mono: string;
    serif: string;
  };
  
  fontSize: {
    xs: string;
    sm: string;
    base: string;
    lg: string;
    xl: string;
    '2xl': string;
    '3xl': string;
    '4xl': string;
    '5xl': string;
    '6xl': string;
  };
  
  fontWeight: {
    thin: number;
    light: number;
    normal: number;
    medium: number;
    semibold: number;
    bold: number;
    extrabold: number;
  };
  
  lineHeight: {
    tight: number;
    normal: number;
    relaxed: number;
    loose: number;
  };
  
  letterSpacing: {
    tight: string;
    normal: string;
    wide: string;
  };
}

export interface Spacing {
  0: string;
  px: string;
  0.5: string;
  1: string;
  1.5: string;
  2: string;
  2.5: string;
  3: string;
  3.5: string;
  4: string;
  5: string;
  6: string;
  7: string;
  8: string;
  9: string;
  10: string;
  11: string;
  12: string;
  14: string;
  16: string;
  20: string;
  24: string;
  28: string;
  32: string;
  36: string;
  40: string;
  44: string;
  48: string;
  52: string;
  56: string;
  60: string;
  64: string;
  72: string;
  80: string;
  96: string;
}

export interface BorderRadius {
  none: string;
  sm: string;
  default: string;
  md: string;
  lg: string;
  xl: string;
  '2xl': string;
  '3xl': string;
  full: string;
}

export interface Shadows {
  sm: string;
  default: string;
  md: string;
  lg: string;
  xl: string;
  '2xl': string;
  inner: string;
  none: string;
}

export interface Breakpoints {
  xs: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
  '2xl': string;
}

export interface ZIndex {
  auto: string;
  0: string;
  10: string;
  20: string;
  30: string;
  40: string;
  50: string;
  dropdown: string;
  modal: string;
  popover: string;
  tooltip: string;
  toast: string;
  overlay: string;
}

export interface Transitions {
  duration: {
    75: string;
    100: string;
    150: string;
    200: string;
    300: string;
    500: string;
    700: string;
    1000: string;
  };
  
  timing: {
    linear: string;
    in: string;
    out: string;
    inOut: string;
  };
}

export interface DesignTokens {
  colors: ThemeColors;
  typography: Typography;
  spacing: Spacing;
  borderRadius: BorderRadius;
  shadows: Shadows;
  breakpoints: Breakpoints;
  zIndex: ZIndex;
  transitions: Transitions;
}

// Color scales
const grayScale: ColorScale = {
  50: '#f9fafb',
  100: '#f3f4f6',
  200: '#e5e7eb',
  300: '#d1d5db',
  400: '#9ca3af',
  500: '#6b7280',
  600: '#4b5563',
  700: '#374151',
  800: '#1f2937',
  900: '#111827',
  950: '#030712',
};

const blueScale: ColorScale = {
  50: '#eff6ff',
  100: '#dbeafe',
  200: '#bfdbfe',
  300: '#93c5fd',
  400: '#60a5fa',
  500: '#3b82f6',
  600: '#2563eb',
  700: '#1d4ed8',
  800: '#1e40af',
  900: '#1e3a8a',
  950: '#172554',
};

const greenScale: ColorScale = {
  50: '#f0fdf4',
  100: '#dcfce7',
  200: '#bbf7d0',
  300: '#86efac',
  400: '#4ade80',
  500: '#22c55e',
  600: '#16a34a',
  700: '#15803d',
  800: '#166534',
  900: '#14532d',
  950: '#052e16',
};

const redScale: ColorScale = {
  50: '#fef2f2',
  100: '#fee2e2',
  200: '#fecaca',
  300: '#fca5a5',
  400: '#f87171',
  500: '#ef4444',
  600: '#dc2626',
  700: '#b91c1c',
  800: '#991b1b',
  900: '#7f1d1d',
  950: '#450a0a',
};

const yellowScale: ColorScale = {
  50: '#fefce8',
  100: '#fef9c3',
  200: '#fef08a',
  300: '#fde047',
  400: '#facc15',
  500: '#eab308',
  600: '#ca8a04',
  700: '#a16207',
  800: '#854d0e',
  900: '#713f12',
  950: '#422006',
};

const purpleScale: ColorScale = {
  50: '#faf5ff',
  100: '#f3e8ff',
  200: '#e9d5ff',
  300: '#d8b4fe',
  400: '#c084fc',
  500: '#a855f7',
  600: '#9333ea',
  700: '#7c3aed',
  800: '#6b21a8',
  900: '#581c87',
  950: '#3b0764',
};

const orangeScale: ColorScale = {
  50: '#fff7ed',
  100: '#ffedd5',
  200: '#fed7aa',
  300: '#fdba74',
  400: '#fb923c',
  500: '#f97316',
  600: '#ea580c',
  700: '#c2410c',
  800: '#9a3412',
  900: '#7c2d12',
  950: '#431407',
};

// Light theme tokens
export const lightTokens: DesignTokens = {
  colors: {
    brand: {
      primary: blueScale[600],
      secondary: purpleScale[600],
      accent: orangeScale[500],
    },
    
    primary: blueScale,
    secondary: purpleScale,
    accent: orangeScale,
    neutral: grayScale,
    success: greenScale,
    warning: yellowScale,
    error: redScale,
    info: blueScale,
    
    surface: {
      background: '#ffffff',
      backgroundSecondary: grayScale[50],
      backgroundTertiary: grayScale[100],
      card: '#ffffff',
      cardSecondary: grayScale[50],
      overlay: 'rgba(0, 0, 0, 0.5)',
      modal: '#ffffff',
    },
    
    text: {
      primary: grayScale[900],
      secondary: grayScale[700],
      tertiary: grayScale[500],
      disabled: grayScale[400],
      inverse: '#ffffff',
      link: blueScale[600],
      linkHover: blueScale[700],
    },
    
    border: {
      default: grayScale[200],
      subtle: grayScale[100],
      strong: grayScale[300],
      interactive: blueScale[300],
      focus: blueScale[500],
      error: redScale[300],
      success: greenScale[300],
      warning: yellowScale[300],
    },
    
    network: {
      online: greenScale[500],
      offline: redScale[500],
      maintenance: yellowScale[500],
      degraded: orangeScale[500],
    },
    
    service: {
      active: greenScale[500],
      inactive: grayScale[400],
      suspended: redScale[500],
      pending: yellowScale[500],
    },
    
    billing: {
      paid: greenScale[500],
      unpaid: yellowScale[500],
      overdue: redScale[500],
      refunded: blueScale[500],
    },
  },
  
  typography: {
    fontFamily: {
      sans: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      mono: '"Fira Code", "JetBrains Mono", Consolas, "Liberation Mono", Menlo, Courier, monospace',
      serif: 'Charter, "Bitstream Charter", "Sitka Text", Cambria, serif',
    },
    
    fontSize: {
      xs: '0.75rem',    // 12px
      sm: '0.875rem',   // 14px
      base: '1rem',     // 16px
      lg: '1.125rem',   // 18px
      xl: '1.25rem',    // 20px
      '2xl': '1.5rem',  // 24px
      '3xl': '1.875rem', // 30px
      '4xl': '2.25rem',  // 36px
      '5xl': '3rem',     // 48px
      '6xl': '3.75rem',  // 60px
    },
    
    fontWeight: {
      thin: 100,
      light: 300,
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
      extrabold: 800,
    },
    
    lineHeight: {
      tight: 1.25,
      normal: 1.5,
      relaxed: 1.625,
      loose: 2,
    },
    
    letterSpacing: {
      tight: '-0.025em',
      normal: '0em',
      wide: '0.025em',
    },
  },
  
  spacing: {
    0: '0px',
    px: '1px',
    0.5: '0.125rem',  // 2px
    1: '0.25rem',     // 4px
    1.5: '0.375rem',  // 6px
    2: '0.5rem',      // 8px
    2.5: '0.625rem',  // 10px
    3: '0.75rem',     // 12px
    3.5: '0.875rem',  // 14px
    4: '1rem',        // 16px
    5: '1.25rem',     // 20px
    6: '1.5rem',      // 24px
    7: '1.75rem',     // 28px
    8: '2rem',        // 32px
    9: '2.25rem',     // 36px
    10: '2.5rem',     // 40px
    11: '2.75rem',    // 44px
    12: '3rem',       // 48px
    14: '3.5rem',     // 56px
    16: '4rem',       // 64px
    20: '5rem',       // 80px
    24: '6rem',       // 96px
    28: '7rem',       // 112px
    32: '8rem',       // 128px
    36: '9rem',       // 144px
    40: '10rem',      // 160px
    44: '11rem',      // 176px
    48: '12rem',      // 192px
    52: '13rem',      // 208px
    56: '14rem',      // 224px
    60: '15rem',      // 240px
    64: '16rem',      // 256px
    72: '18rem',      // 288px
    80: '20rem',      // 320px
    96: '24rem',      // 384px
  },
  
  borderRadius: {
    none: '0px',
    sm: '0.125rem',   // 2px
    default: '0.25rem', // 4px
    md: '0.375rem',   // 6px
    lg: '0.5rem',     // 8px
    xl: '0.75rem',    // 12px
    '2xl': '1rem',    // 16px
    '3xl': '1.5rem',  // 24px
    full: '9999px',
  },
  
  shadows: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    default: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
    '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
    none: '0 0 #0000',
  },
  
  breakpoints: {
    xs: '475px',
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    '2xl': '1536px',
  },
  
  zIndex: {
    auto: 'auto',
    0: '0',
    10: '10',
    20: '20',
    30: '30',
    40: '40',
    50: '50',
    dropdown: '1000',
    modal: '1050',
    popover: '1060',
    tooltip: '1070',
    toast: '1080',
    overlay: '1090',
  },
  
  transitions: {
    duration: {
      75: '75ms',
      100: '100ms',
      150: '150ms',
      200: '200ms',
      300: '300ms',
      500: '500ms',
      700: '700ms',
      1000: '1000ms',
    },
    
    timing: {
      linear: 'linear',
      in: 'cubic-bezier(0.4, 0, 1, 1)',
      out: 'cubic-bezier(0, 0, 0.2, 1)',
      inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    },
  },
};

// Dark theme tokens
export const darkTokens: DesignTokens = {
  ...lightTokens,
  colors: {
    ...lightTokens.colors,
    
    surface: {
      background: grayScale[900],
      backgroundSecondary: grayScale[800],
      backgroundTertiary: grayScale[700],
      card: grayScale[800],
      cardSecondary: grayScale[700],
      overlay: 'rgba(0, 0, 0, 0.7)',
      modal: grayScale[800],
    },
    
    text: {
      primary: grayScale[50],
      secondary: grayScale[300],
      tertiary: grayScale[400],
      disabled: grayScale[500],
      inverse: grayScale[900],
      link: blueScale[400],
      linkHover: blueScale[300],
    },
    
    border: {
      default: grayScale[700],
      subtle: grayScale[800],
      strong: grayScale[600],
      interactive: blueScale[600],
      focus: blueScale[500],
      error: redScale[600],
      success: greenScale[600],
      warning: yellowScale[600],
    },
  },
};

// High contrast theme for accessibility
export const highContrastTokens: DesignTokens = {
  ...lightTokens,
  colors: {
    ...lightTokens.colors,
    
    text: {
      primary: '#000000',
      secondary: '#000000',
      tertiary: '#000000',
      disabled: '#666666',
      inverse: '#ffffff',
      link: '#0000ff',
      linkHover: '#0000cc',
    },
    
    border: {
      default: '#000000',
      subtle: '#333333',
      strong: '#000000',
      interactive: '#0000ff',
      focus: '#ff0000',
      error: '#cc0000',
      success: '#008000',
      warning: '#ff8c00',
    },
  },
};

export type ThemeName = 'light' | 'dark' | 'highContrast';

export const themes: Record<ThemeName, DesignTokens> = {
  light: lightTokens,
  dark: darkTokens,
  highContrast: highContrastTokens,
};
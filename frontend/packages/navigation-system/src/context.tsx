import { createContext, useContext } from 'react';
import type { NavigationContextValue } from './types';

const NavigationContext = createContext<NavigationContextValue>({});

export const useNavigationContext = () => useContext(NavigationContext);

export const NavigationProvider = NavigationContext.Provider;

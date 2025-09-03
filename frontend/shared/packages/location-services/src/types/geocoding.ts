/**
 * Geocoding service type definitions
 */

import type { LocationData } from './location';

export interface AddressComponent {
  longName: string;
  shortName: string;
  types: string[];
}

export interface GeocodingResult {
  address: string;
  location: LocationData;
  accuracy: number;
  components: AddressComponent[];
  placeId?: string;
  formattedAddress: string;
  types: string[];
  metadata?: Record<string, any>;
}

export interface ReverseGeocodingResult {
  location: LocationData;
  addresses: {
    formattedAddress: string;
    components: AddressComponent[];
    accuracy: number;
    types: string[];
    placeId?: string;
  }[];
  metadata?: Record<string, any>;
}

export interface PlaceResult {
  placeId: string;
  name: string;
  address: string;
  location: LocationData;
  types: string[];
  rating?: number;
  priceLevel?: number;
  photos?: PlacePhoto[];
  openingHours?: {
    isOpen: boolean;
    periods: {
      open: { day: number; time: string };
      close?: { day: number; time: string };
    }[];
    weekdayText: string[];
  };
  contact?: {
    phone?: string;
    website?: string;
    email?: string;
  };
  metadata?: Record<string, any>;
}

export interface PlacePhoto {
  url: string;
  width: number;
  height: number;
  attribution: string;
}

export interface GeocodingOptions {
  bounds?: {
    northeast: LocationData;
    southwest: LocationData;
  };
  region?: string; // ISO country code
  language?: string; // ISO language code
  components?: {
    country?: string;
    administrative_area?: string;
    locality?: string;
    postal_code?: string;
  };
  placeTypes?: string[];
}

export interface AutocompleteResult {
  predictions: AutocompletePrediction[];
  status: string;
  metadata?: Record<string, any>;
}

export interface AutocompletePrediction {
  description: string;
  placeId: string;
  types: string[];
  matchedSubstrings: {
    offset: number;
    length: number;
  }[];
  structuredFormatting: {
    mainText: string;
    secondaryText: string;
    mainTextMatchedSubstrings?: {
      offset: number;
      length: number;
    }[];
  };
  terms: {
    offset: number;
    value: string;
  }[];
}

export interface PlaceSearchRequest {
  query?: string;
  location?: LocationData;
  radius?: number; // meters
  types?: string[];
  minRating?: number;
  maxResults?: number;
  openNow?: boolean;
  priceLevel?: number[];
}

export interface PlaceSearchResult {
  places: PlaceResult[];
  nextPageToken?: string;
  metadata?: Record<string, any>;
}

export interface NearbySearchRequest {
  location: LocationData;
  radius: number; // meters
  types?: string[];
  keyword?: string;
  minRating?: number;
  maxResults?: number;
  openNow?: boolean;
}

export interface GeocodingCache {
  key: string;
  result: GeocodingResult | ReverseGeocodingResult;
  timestamp: Date;
  expiresAt: Date;
}

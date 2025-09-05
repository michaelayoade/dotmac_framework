'use client'

import React from 'react'

export function PageLoading() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Loading...</p>
      </div>
    </div>
  )
}

export function ComponentLoading() {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      <span className="ml-2 text-gray-600">Loading...</span>
    </div>
  )
}

export function InlineLoading() {
  return (
    <div className="inline-flex items-center">
      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
      <span className="ml-2 text-sm text-gray-600">Loading...</span>
    </div>
  )
}
/**
 * API Gateway Status Page
 * Dedicated page for monitoring gateway and service health
 */

import React from 'react';
import { NextPage } from 'next';
import Head from 'next/head';
import AdminLayout from '../components/layout/AdminLayout';
import GatewayStatus from '../components/admin/GatewayStatus';
import { useAuth } from '../hooks/useAuth';
import { useRouter } from 'next/router';
import { useEffect } from 'react';

const GatewayStatusPage: NextPage = () => {
  const { isAuthenticated, hasPermission } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    if (!hasPermission('admin') && !hasPermission('system.monitoring')) {
      router.push('/dashboard');
      return;
    }
  }, [isAuthenticated, hasPermission, router]);

  if (!isAuthenticated || (!hasPermission('admin') && !hasPermission('system.monitoring'))) {
    return null;
  }

  return (
    <>
      <Head>
        <title>API Gateway Status - DotMac Admin</title>
        <meta name="description" content="Monitor API gateway and backend service health" />
      </Head>
      
      <AdminLayout>
        <GatewayStatus />
      </AdminLayout>
    </>
  );
};

export default GatewayStatusPage;
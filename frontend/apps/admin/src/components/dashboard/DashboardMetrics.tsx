'use client';

import { ArrowUpIcon, ArrowDownIcon, UsersIcon, WifiIcon, DollarSignIcon, TicketIcon } from 'lucide-react';

interface MetricsData {
  totalCustomers: number;
  activeServices: number;
  monthlyRevenue: number;
  ticketsOpen: number;
  growth: {
    customers: number;
    revenue: number;
    services: number;
  };
}

export function DashboardMetrics({ metrics }: { metrics: MetricsData }) {
  const cards = [
    {
      title: 'Total Customers',
      value: metrics.totalCustomers.toLocaleString(),
      change: metrics.growth.customers,
      icon: UsersIcon,
      color: 'blue',
    },
    {
      title: 'Active Services',
      value: metrics.activeServices.toLocaleString(),
      change: metrics.growth.services,
      icon: WifiIcon,
      color: 'green',
    },
    {
      title: 'Monthly Revenue',
      value: `$${metrics.monthlyRevenue.toLocaleString()}`,
      change: metrics.growth.revenue,
      icon: DollarSignIcon,
      color: 'indigo',
    },
    {
      title: 'Open Tickets',
      value: metrics.ticketsOpen.toString(),
      change: 0,
      icon: TicketIcon,
      color: 'yellow',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => {
        const Icon = card.icon;
        const isPositive = card.change > 0;
        
        return (
          <div key={card.title} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div className={`p-2 rounded-lg bg-${card.color}-100`}>
                <Icon className={`h-6 w-6 text-${card.color}-600`} />
              </div>
              {card.change !== 0 && (
                <div className={`flex items-center text-sm ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                  {isPositive ? (
                    <ArrowUpIcon className="h-4 w-4 mr-1" />
                  ) : (
                    <ArrowDownIcon className="h-4 w-4 mr-1" />
                  )}
                  {Math.abs(card.change)}%
                </div>
              )}
            </div>
            <div className="mt-4">
              <h3 className="text-sm font-medium text-gray-500">{card.title}</h3>
              <p className="mt-1 text-2xl font-semibold text-gray-900">{card.value}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
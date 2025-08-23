"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

interface Plugin {
  id: string;
  name: string;
  category: string;
  description: string;
  version?: string;
  status: "installed" | "available" | "installing" | "error";
  dependencies: string[];
  configTemplate?: string;
  lastUpdated?: string;
}

interface PluginInstallation {
  pluginId: string;
  status: "pending" | "installing" | "success" | "error";
  message?: string;
  progress?: number;
}

const PLUGIN_CATEGORIES = {
  communication: { 
    name: "Communication & Messaging", 
    icon: "📞", 
    color: "blue",
    description: "SMS, email, chat, and notification integrations"
  },
  billing: { 
    name: "Billing & Payments", 
    icon: "💳", 
    color: "green",
    description: "Payment processors, invoicing, and accounting systems"
  },
  network_automation: { 
    name: "Network Management", 
    icon: "🔧", 
    color: "purple",
    description: "Device automation, monitoring, and configuration"
  },
  crm_integration: { 
    name: "CRM & Marketing", 
    icon: "👥", 
    color: "orange",
    description: "Customer relationship management and marketing tools"
  },
  monitoring: { 
    name: "Monitoring & Analytics", 
    icon: "📊", 
    color: "red",
    description: "System monitoring, metrics, and business analytics"
  },
  ticketing: { 
    name: "Support & Ticketing", 
    icon: "🎫", 
    color: "yellow",
    description: "Customer support and help desk systems"
  },
  storage: { 
    name: "Storage & Backup", 
    icon: "💾", 
    color: "indigo",
    description: "File storage, backup, and document management"
  },
  security: { 
    name: "Security & Compliance", 
    icon: "🔒", 
    color: "gray",
    description: "Security scanning, compliance, and audit tools"
  },
};

export default function PluginsPage() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [installations, setInstallations] = useState<PluginInstallation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  useEffect(() => {
    fetchPlugins();
  }, []);

  const fetchPlugins = async () => {
    try {
      setLoading(true);
      
      // In a real implementation, this would call the backend API
      // For now, we'll simulate the plugin data
      const mockPlugins: Plugin[] = [
        {
          id: "twilio",
          name: "Twilio SMS Plugin",
          category: "communication",
          description: "SMS communication via Twilio API",
          status: "available",
          dependencies: ["twilio>=9.7.1"],
        },
        {
          id: "stripe",
          name: "Stripe Payment Plugin", 
          category: "billing",
          description: "Payment processing via Stripe API",
          status: "installed",
          version: "12.4.0",
          dependencies: ["stripe>=12.4.0"],
          lastUpdated: "2024-01-15T10:30:00Z",
        },
        {
          id: "network-automation",
          name: "Network Automation Plugin",
          category: "network_automation",
          description: "Network device automation and monitoring", 
          status: "available",
          dependencies: ["pysnmp>=7.1.21", "paramiko>=4.0.0", "ansible-runner>=2.4.1"],
        },
        {
          id: "sendgrid",
          name: "SendGrid Email Plugin",
          category: "communication", 
          description: "Email delivery via SendGrid API",
          status: "available",
          dependencies: ["sendgrid>=6.10.0"],
        },
        {
          id: "slack",
          name: "Slack Integration Plugin",
          category: "communication",
          description: "Slack notifications and integrations",
          status: "available",
          dependencies: ["slack-sdk>=3.27.0"],
        },
        {
          id: "hubspot",
          name: "HubSpot CRM Plugin",
          category: "crm_integration",
          description: "CRM integration with HubSpot",
          status: "available", 
          dependencies: ["hubspot-api-client>=8.1.0"],
        },
      ];
      
      setPlugins(mockPlugins);
    } catch (err) {
      setError("Failed to load plugins");
      console.error("Error fetching plugins:", err);
    } finally {
      setLoading(false);
    }
  };

  const installPlugin = async (pluginId: string) => {
    try {
      // Add installation tracking
      const installation: PluginInstallation = {
        pluginId,
        status: "installing",
        progress: 0,
      };
      setInstallations(prev => [...prev, installation]);

      // Update plugin status
      setPlugins(prev => 
        prev.map(p => 
          p.id === pluginId ? { ...p, status: "installing" } : p
        )
      );

      // Simulate installation progress
      for (let progress = 0; progress <= 100; progress += 20) {
        await new Promise(resolve => setTimeout(resolve, 500));
        setInstallations(prev => 
          prev.map(inst => 
            inst.pluginId === pluginId 
              ? { ...inst, progress }
              : inst
          )
        );
      }

      // In a real implementation, this would call:
      // const response = await fetch('/api/admin/plugins/install', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ pluginId }),
      // });

      // Simulate success
      setPlugins(prev => 
        prev.map(p => 
          p.id === pluginId 
            ? { ...p, status: "installed", lastUpdated: new Date().toISOString() }
            : p
        )
      );

      setInstallations(prev => 
        prev.map(inst => 
          inst.pluginId === pluginId 
            ? { ...inst, status: "success", message: "Plugin installed successfully!" }
            : inst
        )
      );

      // Remove installation tracking after delay
      setTimeout(() => {
        setInstallations(prev => prev.filter(inst => inst.pluginId !== pluginId));
      }, 3000);

    } catch (err) {
      setPlugins(prev => 
        prev.map(p => 
          p.id === pluginId ? { ...p, status: "error" } : p
        )
      );

      setInstallations(prev => 
        prev.map(inst => 
          inst.pluginId === pluginId 
            ? { ...inst, status: "error", message: "Installation failed" }
            : inst
        )
      );
    }
  };

  const uninstallPlugin = async (pluginId: string) => {
    try {
      setPlugins(prev => 
        prev.map(p => 
          p.id === pluginId ? { ...p, status: "installing" } : p
        )
      );

      // In a real implementation:
      // await fetch(`/api/admin/plugins/${pluginId}/uninstall`, { method: 'DELETE' });

      // Simulate uninstall
      await new Promise(resolve => setTimeout(resolve, 2000));

      setPlugins(prev => 
        prev.map(p => 
          p.id === pluginId ? { ...p, status: "available" } : p
        )
      );
    } catch (err) {
      setPlugins(prev => 
        prev.map(p => 
          p.id === pluginId ? { ...p, status: "error" } : p
        )
      );
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "installed": return "text-green-600";
      case "installing": return "text-blue-600";
      case "error": return "text-red-600";
      default: return "text-gray-600";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "installed": return "✅";
      case "installing": return "⏳";
      case "error": return "❌";
      default: return "⭕";
    }
  };

  const filteredPlugins = selectedCategory === "all" 
    ? plugins 
    : plugins.filter(p => p.category === selectedCategory);

  const categoryCounts = Object.keys(PLUGIN_CATEGORIES).reduce((acc, category) => {
    acc[category] = plugins.filter(p => p.category === category).length;
    return acc;
  }, {} as Record<string, number>);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Plugin Management</h1>
          <p className="text-gray-600">
            Install and manage third-party integrations for your ISP platform
          </p>
        </div>
        
        <Button 
          onClick={fetchPlugins}
          variant="outline"
          disabled={loading}
        >
          🔄 Refresh
        </Button>
      </div>

      {error && (
        <Alert variant="error">
          {error}
        </Alert>
      )}

      {/* Category Filter */}
      <Card>
        <div className="p-4">
          <h3 className="text-lg font-semibold mb-4">Categories</h3>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedCategory("all")}
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                selectedCategory === "all"
                  ? "bg-blue-100 text-blue-700"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              All ({plugins.length})
            </button>
            {Object.entries(PLUGIN_CATEGORIES).map(([key, category]) => (
              <button
                key={key}
                onClick={() => setSelectedCategory(key)}
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  selectedCategory === key
                    ? "bg-blue-100 text-blue-700"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {category.icon} {category.name} ({categoryCounts[key] || 0})
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Plugin Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredPlugins.map((plugin) => {
          const installation = installations.find(inst => inst.pluginId === plugin.id);
          const categoryInfo = PLUGIN_CATEGORIES[plugin.category as keyof typeof PLUGIN_CATEGORIES];
          
          return (
            <Card key={plugin.id} className="relative">
              <div className="p-6">
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center space-x-2">
                    <span className="text-2xl">{categoryInfo?.icon || "🔌"}</span>
                    <div>
                      <h3 className="font-semibold text-gray-900">{plugin.name}</h3>
                      <span className="text-sm text-gray-500">
                        {categoryInfo?.name || plugin.category}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center space-x-1">
                    <span className={`text-sm ${getStatusColor(plugin.status)}`}>
                      {getStatusIcon(plugin.status)}
                    </span>
                    <span className={`text-xs ${getStatusColor(plugin.status)}`}>
                      {plugin.status.toUpperCase()}
                    </span>
                  </div>
                </div>

                <p className="text-gray-600 text-sm mb-4">{plugin.description}</p>

                {plugin.version && (
                  <p className="text-xs text-gray-500 mb-2">
                    Version: {plugin.version}
                  </p>
                )}

                {plugin.lastUpdated && (
                  <p className="text-xs text-gray-500 mb-4">
                    Last updated: {new Date(plugin.lastUpdated).toLocaleDateString()}
                  </p>
                )}

                {installation && installation.status === "installing" && (
                  <div className="mb-4">
                    <div className="flex justify-between text-sm text-gray-600 mb-1">
                      <span>Installing...</span>
                      <span>{installation.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all"
                        style={{ width: `${installation.progress}%` }}
                      />
                    </div>
                  </div>
                )}

                {installation && installation.message && (
                  <Alert 
                    variant={installation.status === "success" ? "success" : "error"}
                    className="mb-4"
                  >
                    {installation.message}
                  </Alert>
                )}

                <div className="flex space-x-2">
                  {plugin.status === "available" && (
                    <Button
                      onClick={() => installPlugin(plugin.id)}
                      size="sm"
                      className="flex-1"
                    >
                      📦 Install
                    </Button>
                  )}
                  
                  {plugin.status === "installed" && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                      >
                        ⚙️ Configure
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => uninstallPlugin(plugin.id)}
                        className="text-red-600 hover:text-red-700"
                      >
                        🗑️
                      </Button>
                    </>
                  )}
                  
                  {plugin.status === "installing" && (
                    <Button
                      size="sm"
                      disabled
                      className="flex-1"
                    >
                      <LoadingSpinner size="sm" /> Installing...
                    </Button>
                  )}
                  
                  {plugin.status === "error" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => installPlugin(plugin.id)}
                      className="flex-1"
                    >
                      🔄 Retry
                    </Button>
                  )}
                </div>

                <details className="mt-4">
                  <summary className="text-xs text-gray-500 cursor-pointer">
                    Dependencies ({plugin.dependencies.length})
                  </summary>
                  <ul className="text-xs text-gray-400 mt-2 space-y-1">
                    {plugin.dependencies.map((dep, idx) => (
                      <li key={idx}>• {dep}</li>
                    ))}
                  </ul>
                </details>
              </div>
            </Card>
          );
        })}
      </div>

      {filteredPlugins.length === 0 && (
        <Card>
          <div className="p-8 text-center text-gray-500">
            <span className="text-4xl mb-4 block">🔍</span>
            <p>No plugins found in this category.</p>
          </div>
        </Card>
      )}
    </div>
  );
}
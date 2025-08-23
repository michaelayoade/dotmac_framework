"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import { 
  Shield, 
  Users, 
  HandHelp, 
  Wrench, 
  ArrowRight,
  Building,
  Globe,
  Search
} from "lucide-react";

interface PortalOption {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  route: string;
  audience: string;
  features: string[];
}

const portalOptions: PortalOption[] = [
  {
    id: "customer",
    title: "Customer Portal",
    description: "Manage your internet services, view bills, and get support",
    icon: Users,
    color: "blue",
    route: "https://customer.dotmac-isp.local:3001",
    audience: "Internet service customers",
    features: [
      "View and pay bills",
      "Monitor internet usage", 
      "Request technical support",
      "Manage service plans",
      "Download invoices"
    ]
  },
  {
    id: "admin",
    title: "Admin Portal", 
    description: "Complete ISP operations management and system administration",
    icon: Shield,
    color: "red",
    route: "https://admin.dotmac-isp.local:3000",
    audience: "ISP administrators and staff",
    features: [
      "Customer management",
      "Network operations",
      "Billing management", 
      "System configuration",
      "Analytics and reporting"
    ]
  },
  {
    id: "reseller",
    title: "Reseller Portal",
    description: "Partner portal for resellers and channel partners",
    icon: HandHelp,
    color: "green", 
    route: "https://reseller.dotmac-isp.local:3003",
    audience: "Authorized reseller partners",
    features: [
      "Customer acquisition",
      "Commission tracking",
      "Territory management",
      "Sales tools and resources",
      "Partner support"
    ]
  },
  {
    id: "technician", 
    title: "Field Technician",
    description: "Mobile app for field technicians and service crews",
    icon: Wrench,
    color: "purple",
    route: "https://technician.dotmac-isp.local:3004",
    audience: "Field service technicians",
    features: [
      "Work order management",
      "Customer site information",
      "Offline capability",
      "GPS navigation",
      "Photo documentation"
    ]
  }
];

export default function PortalDiscoveryPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPortal, setSelectedPortal] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  // Auto-detect user based on URL parameters or stored preferences
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const portalHint = urlParams.get('portal');
    const userType = urlParams.get('type');
    
    // Check for existing authentication
    const existingAuth = localStorage.getItem('portal-preference');
    if (existingAuth && !portalHint) {
      const preference = JSON.parse(existingAuth);
      setSelectedPortal(preference.portal);
    }

    // Auto-select based on URL hint
    if (portalHint && portalOptions.find(p => p.id === portalHint)) {
      setSelectedPortal(portalHint);
    }
  }, []);

  const handlePortalSelect = async (portalId: string) => {
    setIsLoading(true);
    setError(null);

    try {
      // Store user preference
      localStorage.setItem('portal-preference', JSON.stringify({ 
        portal: portalId, 
        timestamp: Date.now() 
      }));

      // Find the portal configuration
      const portal = portalOptions.find(p => p.id === portalId);
      if (!portal) {
        throw new Error("Portal configuration not found");
      }

      // Check if portal is accessible
      const healthCheck = await fetch(`${portal.route}/api/health`);
      if (!healthCheck.ok) {
        throw new Error(`${portal.title} is currently unavailable. Please try again later.`);
      }

      // Redirect to portal
      window.location.href = portal.route;

    } catch (err: any) {
      setError(err.message || "Failed to access portal");
      setIsLoading(false);
    }
  };

  const filteredPortals = portalOptions.filter(portal => 
    portal.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    portal.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    portal.audience.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getColorClasses = (color: string) => {
    const colorMap = {
      blue: "border-blue-200 hover:border-blue-300 hover:shadow-blue-100",
      red: "border-red-200 hover:border-red-300 hover:shadow-red-100", 
      green: "border-green-200 hover:border-green-300 hover:shadow-green-100",
      purple: "border-purple-200 hover:border-purple-300 hover:shadow-purple-100"
    };
    return colorMap[color as keyof typeof colorMap] || colorMap.blue;
  };

  const getIconColor = (color: string) => {
    const colorMap = {
      blue: "text-blue-600",
      red: "text-red-600",
      green: "text-green-600", 
      purple: "text-purple-600"
    };
    return colorMap[color as keyof typeof colorMap] || colorMap.blue;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 py-12 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center mb-6">
            <Globe className="h-12 w-12 text-blue-600 mr-4" />
            <h1 className="text-4xl font-bold text-gray-900">DotMac ISP Platform</h1>
          </div>
          <p className="text-xl text-gray-600 mb-8">
            Choose your portal to access ISP management and services
          </p>

          {/* Search */}
          <div className="max-w-md mx-auto relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <Input
              type="text"
              placeholder="Search portals..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 py-3 text-lg"
            />
          </div>
        </div>

        {error && (
          <Alert variant="error" className="mb-8 max-w-2xl mx-auto">
            {error}
          </Alert>
        )}

        {/* Portal Options Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-2 gap-8 mb-12">
          {filteredPortals.map((portal) => {
            const Icon = portal.icon;
            const isSelected = selectedPortal === portal.id;
            
            return (
              <Card 
                key={portal.id}
                className={`cursor-pointer transition-all duration-300 ${
                  getColorClasses(portal.color)
                } ${
                  isSelected ? 'ring-2 ring-blue-500 shadow-lg' : 'hover:shadow-lg'
                }`}
                onClick={() => setSelectedPortal(portal.id)}
              >
                <div className="p-8">
                  <div className="flex items-start justify-between mb-6">
                    <div className="flex items-center">
                      <div className={`p-3 rounded-lg bg-gray-50 mr-4`}>
                        <Icon className={`h-8 w-8 ${getIconColor(portal.color)}`} />
                      </div>
                      <div>
                        <h3 className="text-xl font-bold text-gray-900 mb-1">
                          {portal.title}
                        </h3>
                        <p className="text-sm text-gray-600 font-medium">
                          {portal.audience}
                        </p>
                      </div>
                    </div>
                    {isSelected && (
                      <div className="text-blue-600">
                        <ArrowRight className="h-6 w-6" />
                      </div>
                    )}
                  </div>

                  <p className="text-gray-700 mb-6 text-lg leading-relaxed">
                    {portal.description}
                  </p>

                  <div className="space-y-2">
                    <h4 className="font-semibold text-gray-900 mb-3">Key Features:</h4>
                    <ul className="space-y-2">
                      {portal.features.slice(0, 3).map((feature, index) => (
                        <li key={index} className="flex items-center text-gray-600">
                          <div className={`w-2 h-2 rounded-full ${
                            portal.color === 'blue' ? 'bg-blue-500' :
                            portal.color === 'red' ? 'bg-red-500' :
                            portal.color === 'green' ? 'bg-green-500' : 'bg-purple-500'
                          } mr-3`} />
                          {feature}
                        </li>
                      ))}
                      {portal.features.length > 3 && (
                        <li className="text-gray-500 text-sm ml-5">
                          +{portal.features.length - 3} more features
                        </li>
                      )}
                    </ul>
                  </div>

                  <Button
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePortalSelect(portal.id);
                    }}
                    disabled={isLoading}
                    className={`w-full mt-6 py-3 text-lg ${
                      isSelected 
                        ? 'bg-blue-600 hover:bg-blue-700' 
                        : 'bg-gray-600 hover:bg-gray-700'
                    }`}
                  >
                    {isLoading && selectedPortal === portal.id ? (
                      "Connecting..."
                    ) : (
                      `Access ${portal.title}`
                    )}
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>

        {/* Help Section */}
        <Card className="max-w-3xl mx-auto bg-blue-50 border-blue-200">
          <div className="p-8 text-center">
            <Building className="h-12 w-12 text-blue-600 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-gray-900 mb-3">
              Need Help Choosing?
            </h3>
            <p className="text-gray-700 mb-6">
              Not sure which portal to use? Contact your ISP administrator or check your 
              welcome email for guidance.
            </p>
            <div className="flex justify-center space-x-4">
              <Button variant="outline">
                Contact Support
              </Button>
              <Button variant="outline">
                View Documentation
              </Button>
            </div>
          </div>
        </Card>

        {/* Footer */}
        <div className="text-center mt-12 text-gray-500">
          <p>© 2024 DotMac ISP Framework. All rights reserved.</p>
          <p className="mt-2">
            <a href="/privacy" className="hover:text-gray-700">Privacy Policy</a>
            {" • "}
            <a href="/terms" className="hover:text-gray-700">Terms of Service</a>
            {" • "}
            <a href="/support" className="hover:text-gray-700">Support</a>
          </p>
        </div>
      </div>
    </div>
  );
}
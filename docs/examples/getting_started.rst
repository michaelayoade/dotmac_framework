Getting Started Guide
=====================

This guide will help you get started with the DotMac platform, from initial setup to implementing your first integration.

.. contents::
   :local:
   :depth: 2

Prerequisites
-------------

Before you begin, ensure you have:

- Python 3.11 or higher
- PostgreSQL 14 or higher  
- Redis 7.0 or higher
- Docker (for development)
- Git

Quick Start
-----------

1. **Clone the Repository**

   .. code-block:: bash

      git clone https://github.com/dotmac/platform.git
      cd platform

2. **Setup Development Environment**

   .. code-block:: bash

      # Copy environment configuration
      cp .env.example .env
      
      # Edit configuration
      nano .env
      
      # Install dependencies
      pip install -r requirements.txt
      npm install

3. **Initialize Database**

   .. code-block:: bash

      # Start PostgreSQL
      sudo systemctl start postgresql
      
      # Create database
      createdb dotmac_db
      
      # Run migrations
      alembic upgrade head

4. **Start the Application**

   .. code-block:: bash

      # Start all services
      docker-compose up -d
      
      # Or start individual components
      python main.py  # API server
      npm run dev     # Frontend

Your First API Call
-------------------

Once the application is running, you can make your first API call:

.. code-block:: python

   import requests

   # Get API health status
   response = requests.get("http://localhost:8000/health")
   print(response.json())
   # Output: {"status": "healthy", "timestamp": "2024-02-01T12:00:00Z"}

   # Get authentication token
   auth_response = requests.post("http://localhost:8000/api/auth/login", json={
       "email": "admin@dotmac.com",
       "password": "your_password"
   })
   token = auth_response.json()["access_token"]

   # Make authenticated API call
   headers = {"Authorization": f"Bearer {token}"}
   customers_response = requests.get(
       "http://localhost:8000/api/identity/customers",
       headers=headers
   )
   customers = customers_response.json()
   print(f"Found {len(customers)} customers")

Creating Your First Customer
-----------------------------

Here's how to create a customer using the DotMac API:

.. code-block:: python

   from dotmac_isp.modules.identity.services.customer_service import CustomerService
   from dotmac_isp.modules.identity.schemas import CustomerCreate
   from dotmac_isp.core.database import get_db

   # Initialize database session
   db = next(get_db())
   tenant_id = "your-tenant-id"

   # Initialize customer service
   customer_service = CustomerService(db, tenant_id)

   # Create customer data
   customer_data = CustomerCreate(
       name="John Doe",
       email="john.doe@example.com", 
       phone="+1-555-0123",
       address="123 Main St, Anytown, ST 12345",
       customer_type="residential"
   )

   # Create the customer
   try:
       customer = await customer_service.create(customer_data)
       print(f"Created customer: {customer.name}")
       print(f"Portal ID: {customer.portal_id}")
       print(f"Customer ID: {customer.id}")
   except Exception as e:
       print(f"Error creating customer: {e}")

Setting Up a Service Plan
--------------------------

Before you can provision services, you need to create service plans:

.. code-block:: python

   from dotmac_isp.modules.services.service import ServicePlanService
   from dotmac_isp.modules.services.schemas import ServicePlanCreate
   from decimal import Decimal

   # Initialize service plan service
   plan_service = ServicePlanService(db, tenant_id)

   # Create a fiber internet plan
   plan_data = ServicePlanCreate(
       name="Fiber 100/100",
       description="100 Mbps symmetric fiber internet",
       service_type="INTERNET",
       monthly_price=Decimal("79.99"),
       setup_fee=Decimal("99.00"),
       is_public=True,
       features={
           "download_speed": "100 Mbps",
           "upload_speed": "100 Mbps", 
           "data_limit": "unlimited",
           "technology": "fiber"
       }
   )

   # Create the plan
   plan = await plan_service.create_plan(plan_data)
   print(f"Created service plan: {plan.name}")

Provisioning a Service
----------------------

Now you can provision a service for a customer:

.. code-block:: python

   from dotmac_isp.modules.services.service import ServiceProvisioningService
   from dotmac_isp.modules.services.schemas import ServiceInstanceCreate

   # Initialize provisioning service
   provisioning_service = ServiceProvisioningService(db, tenant_id)

   # Provision internet service
   service_data = ServiceInstanceCreate(
       customer_id=customer.id,
       service_plan_id=plan.id,
       installation_address="123 Main St, Anytown, ST 12345",
       requested_activation_date="2024-02-15",
       service_config={
           "static_ip": False,
           "wifi_enabled": True,
           "parental_controls": False
       }
   )

   # Create service instance
   service = await provisioning_service.provision_service(service_data)
   print(f"Provisioned service: {service.service_number}")
   print(f"Status: {service.status}")

Creating an Invoice
-------------------

Generate an invoice for the provisioned service:

.. code-block:: python

   from dotmac_isp.modules.billing.services.invoice_service import InvoiceService
   from dotmac_isp.modules.billing.schemas import InvoiceCreate
   from datetime import date, timedelta

   # Initialize invoice service
   invoice_service = InvoiceService(db, tenant_id)

   # Create invoice for first month + setup
   invoice_data = InvoiceCreate(
       customer_id=customer.id,
       due_date=date.today() + timedelta(days=30),
       line_items=[
           {
               "description": f"{plan.name} - Monthly Service",
               "quantity": 1,
               "unit_price": plan.monthly_price,
               "service_instance_id": service.id
           },
           {
               "description": "Installation & Setup Fee", 
               "quantity": 1,
               "unit_price": plan.setup_fee
           }
       ]
   )

   # Generate invoice
   invoice = await invoice_service.create_invoice(invoice_data)
   print(f"Created invoice: {invoice.invoice_number}")
   print(f"Total amount: ${invoice.total_amount}")

Setting Up Monitoring
---------------------

Enable network monitoring for the service:

.. code-block:: python

   from dotmac_isp.modules.network_monitoring.service import NetworkMonitoringService
   from dotmac_isp.modules.network_monitoring.schemas import DeviceCreate

   # Initialize monitoring service
   monitoring_service = NetworkMonitoringService(db, tenant_id)

   # Add customer's router for monitoring
   device_data = DeviceCreate(
       device_name="Customer Router - John Doe",
       device_type="router",
       ip_address="192.168.1.1",
       snmp_community="public",
       customer_id=customer.id,
       service_instance_id=service.id,
       monitoring_enabled=True
   )

   # Add device
   device = await monitoring_service.add_device(device_data)
   print(f"Added device for monitoring: {device.device_name}")

Testing Your Setup
------------------

Verify everything is working correctly:

.. code-block:: python

   # Test customer portal access
   from dotmac_isp.modules.identity.services.auth_service import AuthService

   auth_service = AuthService(db, tenant_id)

   # Test portal authentication
   portal_auth = await auth_service.authenticate_portal_user(
       portal_id=customer.portal_id,
       password="customer_password"  # Set during customer creation
   )

   if portal_auth.success:
       print("Customer portal access working!")
   else:
       print(f"Portal auth failed: {portal_auth.error}")

   # Test service status
   service_status = await provisioning_service.get_service_status(service.id)
   print(f"Service status: {service_status}")

   # Test monitoring
   device_status = await monitoring_service.get_device_status(device.id)
   print(f"Device status: {device_status}")

Frontend Integration
--------------------

Connect to the React frontend components:

.. code-block:: typescript

   // Install the headless package
   npm install @dotmac/headless

   // Use in your React component
   import { useISPTenant, useCustomers } from '@dotmac/headless';

   function CustomerList() {
     const { session } = useISPTenant();
     const { data: customers, isLoading } = useCustomers();

     if (isLoading) return <div>Loading customers...</div>;

     return (
       <div>
         <h1>Customers for {session?.tenant.company_name}</h1>
         {customers?.map(customer => (
           <div key={customer.id}>
             {customer.name} - {customer.portal_id}
           </div>
         ))}
       </div>
     );
   }

Next Steps
----------

Now that you have the basics working, you can:

1. **Explore Advanced Features**:
   - Multi-tenant management
   - Advanced billing scenarios
   - Network topology visualization
   - Customer portal customization

2. **Integrate External Systems**:
   - Payment processors
   - Network equipment APIs
   - Customer communication tools
   - Accounting software

3. **Customize the Platform**:
   - Add custom fields to models
   - Create custom workflows
   - Build specialized reports
   - Implement custom integrations

4. **Deploy to Production**:
   - Follow the :doc:`DEPLOYMENT_GUIDE`
   - Set up monitoring and alerting
   - Configure backups
   - Implement security hardening

Additional Resources
-------------------

- :doc:`../api_reference` - Complete API documentation
- :doc:`../troubleshooting` - Common issues and solutions
- :doc:`../ARCHITECTURE` - Platform architecture overview
- :doc:`advanced_usage` - Advanced integration patterns

Need Help?
----------

If you run into issues:

1. Check the :doc:`../troubleshooting` guide
2. Review the API documentation
3. Check the application logs
4. Contact support at support@dotmac.com
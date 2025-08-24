Identity Module
===============

The Identity module handles customer management, user authentication, and portal access control.

Overview
--------

The Identity module provides:

* Customer lifecycle management
* Portal ID generation and authentication
* User management and permissions
* Customer intelligence and health scoring
* Multi-tenant access control

.. note::
   This module integrates with the Portal Management system to provide secure,
   tenant-aware authentication across all DotMac portals.

Router & API Endpoints
----------------------

.. automodule:: dotmac_isp.modules.identity.router
   :members:
   :undoc-members:
   :show-inheritance:

Models
------

.. automodule:: dotmac_isp.modules.identity.models
   :members:
   :undoc-members:
   :show-inheritance:

Services
--------

Customer Service
~~~~~~~~~~~~~~~~

.. automodule:: dotmac_isp.modules.identity.services.customer_service
   :members:
   :undoc-members:
   :show-inheritance:

Authentication Service
~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: dotmac_isp.modules.identity.services.auth_service
   :members:
   :undoc-members:
   :show-inheritance:

User Service
~~~~~~~~~~~~

.. automodule:: dotmac_isp.modules.identity.services.user_service
   :members:
   :undoc-members:
   :show-inheritance:

Intelligence Service
~~~~~~~~~~~~~~~~~~~~

.. automodule:: dotmac_isp.modules.identity.intelligence_service
   :members:
   :undoc-members:
   :show-inheritance:

Portal Services
---------------

Portal ID Generator
~~~~~~~~~~~~~~~~~~~

.. automodule:: dotmac_isp.modules.identity.portal_id_generator
   :members:
   :undoc-members:
   :show-inheritance:

Portal Service
~~~~~~~~~~~~~~

.. automodule:: dotmac_isp.modules.identity.portal_service
   :members:
   :undoc-members:
   :show-inheritance:

Schemas
-------

.. automodule:: dotmac_isp.modules.identity.schemas
   :members:
   :undoc-members:
   :show-inheritance:

Repository
----------

.. automodule:: dotmac_isp.modules.identity.repository
   :members:
   :undoc-members:
   :show-inheritance:

Usage Examples
--------------

Creating a Customer
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dotmac_isp.modules.identity.services.customer_service import CustomerService
   from dotmac_isp.modules.identity.schemas import CustomerCreate

   # Initialize service
   customer_service = CustomerService(db_session, tenant_id)

   # Create customer data
   customer_data = CustomerCreate(
       name="John Doe",
       email="john@example.com",
       phone="+1-555-0123",
       address="123 Main St, City, State"
   )

   # Create customer
   customer = await customer_service.create(customer_data)
   print(f"Created customer with Portal ID: {customer.portal_id}")

Customer Health Scoring
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dotmac_isp.modules.identity.intelligence_service import CustomerIntelligenceService

   # Initialize intelligence service
   intelligence = CustomerIntelligenceService(db_session, tenant_id)

   # Get customer health scores
   health_data = await intelligence.get_customer_health_scores()

   # Check for at-risk customers
   for customer_id, health in health_data['customer_health'].items():
       if health['churn_risk']:
           print(f"Customer {customer_id} is at risk: {health['score']}/100")

Portal Authentication
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dotmac_isp.modules.identity.services.auth_service import AuthService

   # Authenticate user
   auth_service = AuthService(db_session, tenant_id)
   
   result = await auth_service.authenticate_user(
       email="john@example.com",
       password="secure_password"
   )
   
   if result.success:
       print(f"Authentication successful. Token: {result.access_token}")
   else:
       print(f"Authentication failed: {result.error}")

Security Considerations
-----------------------

.. warning::
   **Portal ID Security**: Portal IDs are used for customer authentication and should be treated as sensitive data. Never log Portal IDs in plain text or expose them in error messages.

.. important::
   **Multi-Tenant Isolation**: All identity operations are tenant-scoped. Ensure proper tenant context is maintained throughout the request lifecycle.

.. tip::
   **Customer Health Monitoring**: Use the intelligence service to proactively identify at-risk customers and implement retention strategies.
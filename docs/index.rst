.. DotMac Platform documentation master file

=================================
DotMac Platform Documentation
=================================

.. toctree::
   :maxdepth: 2
   :caption: Overview

   README
   ARCHITECTURE
   DEPLOYMENT_GUIDE
   DEVELOPER_ONBOARDING

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   API_DOCUMENTATION
   api_reference

.. toctree::
   :maxdepth: 2
   :caption: Examples & Tutorials

   examples/getting_started
   examples/advanced_usage
   examples/integration_patterns

.. toctree::
   :maxdepth: 2
   :caption: Operations & Support

   troubleshooting
   monitoring
   security
   performance_tuning

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Welcome to DotMac Platform
===========================

The DotMac Platform is a comprehensive enterprise ISP management solution built with modern technologies and best practices.

Key Features
------------

* **Multi-tenant Architecture**: Complete isolation between tenants
* **Enterprise Security**: SSL/TLS encryption, rate limiting, and comprehensive audit trails
* **High Availability**: PostgreSQL replication, Redis clustering, and automatic failover
* **Performance Monitoring**: Real-time metrics, slow query detection, and performance optimization
* **Scalable Design**: Horizontal scaling support with Kubernetes deployment

Quick Links
-----------

* :doc:`ARCHITECTURE` - System architecture and design patterns
* :doc:`API_DOCUMENTATION` - Complete API reference
* :doc:`DEPLOYMENT_GUIDE` - Production deployment instructions
* :doc:`DEVELOPER_ONBOARDING` - Getting started guide for developers

Core Modules
------------

.. automodule:: dotmac_isp.core
   :members:
   :undoc-members:
   :show-inheritance:

Rate Limiting
~~~~~~~~~~~~~

.. automodule:: dotmac_isp.core.rate_limiter
   :members:
   :undoc-members:
   :show-inheritance:

Database Monitoring
~~~~~~~~~~~~~~~~~~~

.. automodule:: dotmac_isp.core.db_monitoring
   :members:
   :undoc-members:
   :show-inheritance:

Encryption Services
~~~~~~~~~~~~~~~~~~~

.. automodule:: dotmac_isp.core.encryption
   :members:
   :undoc-members:
   :show-inheritance:

# DotMac Business Logic Package

Comprehensive business logic components for enterprise applications. This package aggregates related functionality following DRY principles for better maintainability.

## Key Modules

### 🔄 Tasks Module
- **Background Processing**: Celery integration for async task execution
- **Workflows**: Multi-step business process orchestration
- **Job Scheduling**: Cron-like scheduling with monitoring
- **Task Management**: Queue management and worker coordination

### 💰 Billing Module  
- **Invoicing**: Generate, send, and track invoices
- **Payment Processing**: Multiple payment gateway support
- **Subscriptions**: Recurring billing and lifecycle management
- **Multi-Currency**: Exchange rates and currency conversion

### 📄 Files Module
- **Document Generation**: PDF, Excel, Word document creation
- **Template Engine**: Jinja2-based template processing
- **File Processing**: Upload, validation, and transformation
- **Cache Integration**: Redis-based caching for performance

## Benefits of Aggregated Approach

✅ **DRY Principles**: Shared utilities in dotmac-core, no duplication  
✅ **Logical Grouping**: Related functionality packaged together  
✅ **Production Ready**: Each component is comprehensive and tested  
✅ **Clear Dependencies**: Well-defined module boundaries  
✅ **Easier Maintenance**: Fewer packages to manage and version  

## Installation

```bash
pip install dotmac-business-logic
```

### Optional Dependencies

```bash
# For full billing features
pip install dotmac-business-logic[stripe,paypal,pdf]

# For advanced task processing
pip install dotmac-business-logic[rabbitmq,kafka]

# For document generation
pip install dotmac-business-logic[pdf,excel]

# Everything
pip install dotmac-business-logic[all]
```

## Usage

### Task Processing

```python
from dotmac_business_logic.tasks import TaskEngine, WorkflowManager

# Background task processing
task_engine = TaskEngine(broker_url="redis://localhost:6379")
result = await task_engine.execute_async("process_data", {"data": "..."})

# Workflow orchestration
workflow = WorkflowManager()
workflow.add_step("validate", validate_data)
workflow.add_step("process", process_data)
workflow.add_step("notify", send_notification)
await workflow.execute(initial_data)
```

### Billing Operations

```python
from dotmac_business_logic.billing import BillingService, Invoice

# Invoice management
billing = BillingService(config)
invoice = await billing.create_invoice(
    customer_id="cust_123",
    line_items=[
        {"description": "Premium Plan", "amount": 99.00},
        {"description": "Setup Fee", "amount": 50.00}
    ]
)

# Send invoice
await billing.send_invoice(invoice.id, email="customer@example.com")
```

### File Processing

```python
from dotmac_business_logic.files import TemplateEngine, DocumentGenerator

# Template processing
template_engine = TemplateEngine()
html_content = template_engine.render(
    "invoice_template.html",
    {"customer": customer_data, "items": line_items}
)

# Document generation  
doc_gen = DocumentGenerator()
pdf_bytes = await doc_gen.html_to_pdf(html_content)
```

## Architecture

```
dotmac-business-logic/
├── tasks/           # Background processing & workflows
│   ├── engine.py    # Task execution engine
│   ├── queue.py     # Queue management
│   ├── worker.py    # Background workers
│   └── workflow.py  # Workflow orchestration
├── billing/         # Financial operations
│   ├── services/    # Business logic services
│   ├── models/      # Data models
│   └── schemas/     # API schemas
└── files/           # Document & file management
    ├── templates/   # Template processing
    ├── generators/  # Document generation
    └── processors/  # File processing
```

## Contributing

See the main [DotMac Framework](https://github.com/dotmac-framework) repository for contribution guidelines.

## License

MIT License - see LICENSE file for details.
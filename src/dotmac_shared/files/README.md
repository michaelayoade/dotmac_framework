# DotMac File Service

A comprehensive file generation and document processing service for the DotMac platform ecosystem.

## Features

### 🎯 **Core Capabilities**

- **PDF Generation**: Advanced PDF creation with ReportLab
- **Excel Export**: Comprehensive spreadsheet generation with styling
- **CSV Export**: Fast and reliable data export
- **Template Engine**: Jinja2-based template system with caching
- **Image Processing**: Chart generation, QR codes, thumbnails, and watermarking
- **Multi-tenant Storage**: Isolated file storage with quotas and access control

### 🏗️ **Architecture**

```
dotmac_shared/files/
├── core/                    # Core file generation components
│   ├── generators.py        # PDF, Excel, CSV generators
│   ├── templates.py         # Jinja2 template engine
│   └── processors.py        # Image processing utilities
├── storage/                 # Storage abstraction layer
│   ├── backends.py          # Local, S3, Azure storage backends
│   └── tenant_storage.py    # Multi-tenant storage manager
├── adapters/               # Platform-specific adapters
│   ├── isp_adapter.py      # ISP Framework integration
│   └── management_adapter.py # Management Platform integration
└── templates/              # Document templates
    ├── invoice/            # Invoice templates
    ├── reports/            # Report templates
    └── custom/             # Custom templates
```

## Quick Start

### Installation

```bash
cd /home/dotmac_framework/src/dotmac_shared/files
pip install -e .
```

### Basic Usage

```python
from dotmac_files import PDFGenerator, ExcelGenerator, TemplateEngine
from dotmac_files.storage import LocalFileStorage, TenantStorageManager

# Initialize components
storage = LocalFileStorage("/path/to/files")
tenant_storage = TenantStorageManager(storage)
pdf_generator = PDFGenerator()

# Generate an invoice
invoice_data = {
    'invoice_number': 'INV-2023-001',
    'invoice_date': '2023-12-01',
    'customer_info': {
        'name': 'John Doe',
        'email': 'john@example.com'
    },
    'items': [{
        'description': 'Internet Service',
        'quantity': 1,
        'unit_price': 49.99,
        'total': 49.99
    }],
    'total_amount': 49.99
}

file_path, metadata = pdf_generator.generate_invoice(
    invoice_data,
    tenant_id="tenant-123"
)
```

### ISP Platform Integration

```python
from dotmac_files.adapters import ISPFileAdapter
from dotmac_files.adapters.isp_adapter import ISPCustomerInfo, ISPServiceUsage

# Initialize ISP adapter
isp_adapter = ISPFileAdapter(tenant_storage)

# Generate customer invoice
customer = ISPCustomerInfo(
    customer_id="CUST-001",
    name="Tech Company Inc.",
    email="billing@techcompany.com"
)

invoice_path, metadata = await isp_adapter.generate_customer_invoice(
    customer_info=customer,
    invoice_data=invoice_data,
    tenant_id="isp-tenant-123"
)

# Generate usage report
usage_data = [
    ISPServiceUsage(
        service_name="Broadband Internet",
        usage_amount=150.5,
        usage_unit="GB",
        billing_rate=0.10,
        total_cost=15.05,
        period_start=datetime(2023, 12, 1),
        period_end=datetime(2023, 12, 31)
    )
]

report_path, metadata = await isp_adapter.generate_usage_report(
    customer_id="CUST-001",
    usage_data=usage_data,
    date_range={'start': '2023-12-01', 'end': '2023-12-31'},
    tenant_id="isp-tenant-123",
    format="pdf"
)
```

### Management Platform Integration

```python
from dotmac_files.adapters import ManagementPlatformAdapter
from dotmac_files.adapters.management_adapter import TenantInfo, SystemMetrics

# Initialize Management Platform adapter
mgmt_adapter = ManagementPlatformAdapter(tenant_storage)

# Generate tenant report
tenant_info = TenantInfo(
    tenant_id="tenant-123",
    name="Acme Corp",
    contact_email="admin@acme.com",
    created_at=datetime.now(),
    status="active",
    subscription_plan="enterprise",
    user_count=25,
    storage_used=500 * 1024 * 1024,  # 500MB
    storage_quota=1024 * 1024 * 1024  # 1GB
)

report_path, metadata = await mgmt_adapter.generate_tenant_report(
    tenant_info=tenant_info,
    report_type="usage",
    data={'usage_stats': {'api_calls': 1500, 'storage_gb': 0.5}},
    admin_tenant_id="admin-tenant"
)
```

## Template System

### Custom Templates

Create Jinja2 templates for your documents:

```html
<!-- templates/custom/my_report.html -->
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
</head>
<body>
    <h1>{{ title }}</h1>
    <p>Generated: {{ now('%Y-%m-%d') }}</p>

    <table>
        <thead>
            <tr>
                <th>Item</th>
                <th>Value</th>
            </tr>
        </thead>
        <tbody>
            {% for item in data %}
            <tr>
                <td>{{ item.name }}</td>
                <td>{{ item.value | currency }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
```

### Using Templates

```python
template_engine = TemplateEngine()

content = template_engine.render_template(
    'custom/my_report.html',
    context={
        'title': 'Monthly Report',
        'data': [
            {'name': 'Revenue', 'value': 1500.00},
            {'name': 'Expenses', 'value': 800.00}
        ]
    },
    tenant_id="tenant-123"
)
```

## Storage Backends

### Local Storage

```python
from dotmac_files.storage import LocalFileStorage

storage = LocalFileStorage(base_path="/var/dotmac/files")
```

### AWS S3 Storage

```python
from dotmac_files.storage import S3FileStorage

s3_storage = S3FileStorage(
    bucket_name="my-bucket",
    aws_access_key_id="your-key",
    aws_secret_access_key="your-secret",
    region_name="us-west-2"
)
```

### Multi-tenant Storage

```python
from dotmac_files.storage import TenantStorageManager, TenantQuota

# Set tenant quotas
quota = TenantQuota(
    max_storage_bytes=1024 * 1024 * 1024,  # 1GB
    max_files=10000,
    allowed_file_types={'pdf', 'xlsx', 'png', 'jpg'},
    max_file_size=100 * 1024 * 1024  # 100MB
)

tenant_storage = TenantStorageManager(storage)
tenant_storage.set_tenant_quota("tenant-123", quota)

# Check tenant usage
usage = await tenant_storage.get_tenant_usage("tenant-123")
print(f"Storage used: {usage.total_bytes / (1024*1024):.1f} MB")
```

## Image Processing

### Chart Generation

```python
from dotmac_files.core.processors import ImageProcessor

processor = ImageProcessor()

# Generate bar chart
chart_data = {
    'labels': ['Jan', 'Feb', 'Mar', 'Apr'],
    'values': [100, 150, 120, 180]
}

chart_path, metadata = processor.generate_chart(
    'bar',
    chart_data,
    style_config={'title': 'Monthly Sales'}
)
```

### QR Code Generation

```python
qr_path, metadata = processor.generate_qr_code(
    'https://portal.dotmac.com/invoice/123',
    size=(200, 200),
    style_config={
        'fill_color': 'darkblue',
        'back_color': 'white'
    }
)
```

### Image Watermarking

```python
watermarked_path, metadata = processor.add_watermark(
    '/path/to/image.jpg',
    'CONFIDENTIAL',
    position='bottom-right',
    style_config={
        'opacity': 128,
        'color': (255, 0, 0),
        'font_size': 24
    }
)
```

## Configuration

### Environment Variables

```bash
# Storage configuration
FILE_STORAGE_BACKEND=local
FILE_STORAGE_PATH=/var/dotmac/files
MAX_FILE_SIZE_MB=100

# AWS S3 (if using S3 backend)
AWS_S3_BUCKET=my-file-bucket
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret

# Template configuration
TEMPLATE_CACHE_TTL=3600
TEMPLATE_DIR=/path/to/templates

# Processing configuration
ASYNC_PROCESSING=true
MAX_CONCURRENT_JOBS=10
```

### Python Configuration

```python
config = {
    'storage': {
        'backend': 'local',
        'local_path': '/var/dotmac/files',
        'max_file_size': 100 * 1024 * 1024
    },
    'pdf': {
        'page_size': 'letter',
        'margins': 72,
        'font_family': 'Helvetica'
    },
    'templates': {
        'cache_ttl': 3600,
        'auto_escape': True
    }
}
```

## Development

### Running Tests

```bash
pytest tests/ -v --cov=dotmac_files
```

### Code Quality

```bash
# Format code
black dotmac_files/ tests/

# Check imports
isort dotmac_files/ tests/

# Lint code
flake8 dotmac_files/

# Type checking
mypy dotmac_files/
```

## Performance Considerations

- **Template Caching**: Templates are cached to improve performance
- **Streaming**: Large files use streaming to reduce memory usage
- **Async Processing**: Background processing for time-intensive operations
- **Image Optimization**: Automatic image compression and optimization
- **Storage Efficiency**: Efficient storage patterns and cleanup

## Security Features

- **Template Sandboxing**: Jinja2 sandboxed environment prevents code injection
- **Input Sanitization**: All user inputs are sanitized
- **Tenant Isolation**: Complete isolation between tenant data
- **File Type Validation**: Restricted file types and size limits
- **Access Control**: Role-based access to file operations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For support and questions:

- Documentation: <https://docs.dotmac.com/file-service>
- Issues: <https://github.com/dotmac/file-service/issues>
- Email: <support@dotmac.com>

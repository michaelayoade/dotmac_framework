# DotMac Platform SDKs

Official SDKs for the DotMac Platform API.

## Available SDKs

### 🐍 Python
- Location: `sdk/python/`
- Package: `dotmac-platform-sdk`
- [Documentation](https://docs.dotmac.com/sdk/python)

### 📘 TypeScript/JavaScript
- Location: `sdk/typescript/`
- Package: `@dotmac/platform-sdk`
- [Documentation](https://docs.dotmac.com/sdk/typescript)

### 🐹 Go
- Location: `sdk/go/`
- Module: `github.com/dotmac/platform-sdk-go`
- [Documentation](https://docs.dotmac.com/sdk/go)

## Installation

### Python
```bash
pip install dotmac-platform-sdk
```

### TypeScript/JavaScript
```bash
npm install @dotmac/platform-sdk
```

### Go
```bash
go get github.com/dotmac/platform-sdk-go
```

## Authentication

All SDKs support two authentication methods:

1. **API Key**: Use `X-API-Key` header
2. **JWT Token**: Use `Authorization: Bearer <token>` header

## Quick Start

See individual SDK README files for language-specific examples.

## API Documentation

- [OpenAPI Specification](../docs/api/openapi.json)
- [Interactive Documentation](https://api.dotmac.com/docs)
- [Webhook Events](../docs/webhooks/WEBHOOK_EVENTS.md)

## Contributing

SDKs are auto-generated from the OpenAPI specification. To update:

1. Update the OpenAPI spec
2. Run `python scripts/generate_sdk.py`
3. Test the generated SDKs
4. Submit a pull request

## Support

- Documentation: https://docs.dotmac.com
- Issues: https://github.com/dotmac/platform-sdks/issues
- Email: sdk@dotmac.com

## License

MIT License - See LICENSE file for details.

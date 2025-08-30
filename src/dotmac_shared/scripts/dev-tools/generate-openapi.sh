#!/usr/bin/env bash
set -euo pipefail

# DotMac OpenAPI Documentation Generator
# Generates OpenAPI specifications for all services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Default configuration
DEFAULT_OUTPUT_DIR="${PROJECT_ROOT}/docs/api"
DEFAULT_FORMAT="yaml"
DEFAULT_SERVICES="all"

# Configuration from environment
OUTPUT_DIR="${OUTPUT_DIR:-$DEFAULT_OUTPUT_DIR}"
FORMAT="${FORMAT:-$DEFAULT_FORMAT}"
SERVICES="${SERVICES:-$DEFAULT_SERVICES}"

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Generate OpenAPI documentation for DotMac services.

OPTIONS:
    -h, --help              Show this help message
    -o, --output DIR        Output directory (default: docs/api)
    -f, --format FORMAT     Output format (yaml|json|both) (default: yaml)
    -s, --services LIST     Services to document (all|service1,service2) (default: all)
    -p, --port PORT         API port for live documentation (default: 8000)
    --serve                 Serve documentation locally
    --validate              Validate generated specifications

EXAMPLES:
    $0                                          # Generate all docs in YAML
    $0 -f json                                 # Generate in JSON format
    $0 -s "identity,billing"                   # Generate specific services
    $0 --serve                                 # Generate and serve docs

ENVIRONMENT VARIABLES:
    OUTPUT_DIR            Output directory for generated docs
    FORMAT                Output format
    SERVICES              Services to document
EOF
}

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

error() {
    echo "[ERROR] $*" >&2
    exit 1
}

check_dependencies() {
    command -v python3 >/dev/null 2>&1 || error "Python 3 is not installed"

    # Check if the generate script exists
    [ -f "${PROJECT_ROOT}/scripts/generate_openapi_docs.py" ] || error "OpenAPI generator script not found"
}

get_service_list() {
    if [ "$SERVICES" = "all" ]; then
        echo "analytics,api_gateway,billing,core_events,core_ops,devtools,identity,networking,platform,services"
    else
        echo "$SERVICES"
    fi
}

generate_openapi() {
    log "Generating OpenAPI documentation..."

    # Create output directory
    mkdir -p "$OUTPUT_DIR"

    # Get list of services
    local service_list
    service_list=$(get_service_list)

    log "Services: $service_list"
    log "Output directory: $OUTPUT_DIR"
    log "Format: $FORMAT"

    # Run the Python generator
    cd "$PROJECT_ROOT"

    python3 scripts/generate_openapi_docs.py \
        --output-dir "$OUTPUT_DIR" \
        --format "$FORMAT" \
        --services "$service_list"

    log "OpenAPI documentation generated successfully"
}

validate_specs() {
    log "Validating OpenAPI specifications..."

    # Check if swagger-codegen or openapi-generator is available
    if command -v swagger-codegen >/dev/null 2>&1; then
        validator="swagger-codegen"
    elif command -v openapi-generator >/dev/null 2>&1; then
        validator="openapi-generator"
    else
        log "Warning: No OpenAPI validator found. Skipping validation."
        return 0
    fi

    # Validate each generated file
    for file in "$OUTPUT_DIR"/*.{yaml,json}; do
        if [ -f "$file" ]; then
            log "Validating $file..."
            case "$validator" in
                swagger-codegen)
                    swagger-codegen validate -i "$file" || error "Validation failed for $file"
                    ;;
                openapi-generator)
                    openapi-generator validate -i "$file" || error "Validation failed for $file"
                    ;;
            esac
        fi
    done

    log "All specifications validated successfully"
}

serve_docs() {
    local port="$1"

    log "Serving OpenAPI documentation on port $port..."

    # Create a simple index.html if it doesn't exist
    if [ ! -f "${OUTPUT_DIR}/index.html" ]; then
        create_index_html
    fi

    # Start a simple HTTP server
    cd "$OUTPUT_DIR"

    if command -v python3 >/dev/null 2>&1; then
        python3 -m http.server "$port"
    elif command -v python >/dev/null 2>&1; then
        python -m SimpleHTTPServer "$port"
    else
        error "Python is required to serve documentation"
    fi
}

create_index_html() {
    log "Creating documentation index..."

    cat > "${OUTPUT_DIR}/index.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>DotMac API Documentation</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        .service { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .service h2 { margin-top: 0; color: #555; }
        .links a { margin-right: 15px; text-decoration: none; color: #007bff; }
        .links a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>DotMac API Documentation</h1>
    <p>Generated OpenAPI specifications for all DotMac services.</p>

    <div id="services"></div>

    <script>
        // Dynamically load service list
        const services = [
            'analytics', 'api_gateway', 'billing', 'core_events', 'core_ops',
            'devtools', 'identity', 'networking', 'platform', 'services'
        ];

        const container = document.getElementById('services');

        services.forEach(service => {
            const div = document.createElement('div');
            div.className = 'service';

            div.innerHTML = `
                <h2>DotMac ${service.replace('_', ' ').toUpperCase()}</h2>
                <div class="links">
                    <a href="${service}.yaml" target="_blank">YAML Spec</a>
                    <a href="${service}.json" target="_blank">JSON Spec</a>
                </div>
            `;

            container.appendChild(div);
        });
    </script>
</body>
</html>
EOF
}

main() {
    local serve=false
    local validate=false
    local port=8080

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            -f|--format)
                FORMAT="$2"
                shift 2
                ;;
            -s|--services)
                SERVICES="$2"
                shift 2
                ;;
            -p|--port)
                port="$2"
                shift 2
                ;;
            --serve)
                serve=true
                shift
                ;;
            --validate)
                validate=true
                shift
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done

    # Validate format
    case "$FORMAT" in
        yaml|json|both)
            log "Format: $FORMAT"
            ;;
        *)
            error "Invalid format: $FORMAT. Must be one of: yaml, json, both"
            ;;
    esac

    # Check dependencies
    check_dependencies

    log "Generating DotMac OpenAPI documentation..."
    log "Output directory: $OUTPUT_DIR"
    log "Format: $FORMAT"
    log "Services: $SERVICES"

    # Generate documentation
    generate_openapi

    # Validate if requested
    if [ "$validate" = true ]; then
        validate_specs
    fi

    # Serve if requested
    if [ "$serve" = true ]; then
        serve_docs "$port"
    else
        log "Documentation generated successfully in: $OUTPUT_DIR"
        log "To serve locally: $0 --serve"
    fi
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

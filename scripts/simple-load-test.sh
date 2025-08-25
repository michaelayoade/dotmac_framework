#!/bin/bash
# Simple Load Testing for DotMac Platform using curl and existing tools

set -euo pipefail

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
CONCURRENT_USERS="${CONCURRENT_USERS:-10}"
REQUESTS_PER_USER="${REQUESTS_PER_USER:-50}"
TEST_DURATION="${TEST_DURATION:-60}"
OUTPUT_DIR="${OUTPUT_DIR:-/tmp/dotmac-load-test}"

# Create output directory
mkdir -p "$OUTPUT_DIR"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Check if services are running
check_services() {
    log "Checking if DotMac services are running..."
    
    if ! curl -s -f "$BASE_URL/health" > /dev/null; then
        echo "❌ DotMac API is not responding at $BASE_URL"
        exit 1
    fi
    
    log "✅ Services are running"
}

# Simple load test using curl
run_curl_load_test() {
    local endpoint="$1"
    local user_id="$2"
    local requests="$3"
    local output_file="$OUTPUT_DIR/user_${user_id}_results.txt"
    
    log "User $user_id starting load test on $endpoint"
    
    for ((i=1; i<=requests; i++)); do
        curl -s -w "%{http_code},%{time_total},%{time_connect},%{time_starttransfer}\n" \
             -o /dev/null \
             "$BASE_URL$endpoint" >> "$output_file"
        
        # Small delay to prevent overwhelming
        sleep 0.1
    done
    
    log "User $user_id completed $requests requests"
}

# Generate load test report
generate_report() {
    local total_requests=0
    local successful_requests=0
    local failed_requests=0
    local response_times=()
    
    log "Generating load test report..."
    
    # Combine all results
    cat "$OUTPUT_DIR"/user_*_results.txt > "$OUTPUT_DIR/combined_results.csv"
    
    # Process results
    while IFS=',' read -r http_code total_time connect_time transfer_time; do
        ((total_requests++))
        
        if [[ "$http_code" -ge 200 && "$http_code" -lt 400 ]]; then
            ((successful_requests++))
        else
            ((failed_requests++))
        fi
        
        # Collect response times (convert to milliseconds)
        response_times+=($(echo "$total_time * 1000" | bc -l))
        
    done < "$OUTPUT_DIR/combined_results.csv"
    
    # Calculate statistics
    local success_rate=$(echo "scale=2; $successful_requests * 100 / $total_requests" | bc -l)
    local requests_per_second=$(echo "scale=2; $total_requests / $TEST_DURATION" | bc -l)
    
    # Calculate average response time
    local total_time=0
    for time in "${response_times[@]}"; do
        total_time=$(echo "$total_time + $time" | bc -l)
    done
    local avg_response_time=$(echo "scale=2; $total_time / $total_requests" | bc -l)
    
    # Sort response times for percentiles
    printf '%s\n' "${response_times[@]}" | sort -n > "$OUTPUT_DIR/sorted_times.txt"
    local p95_line=$(echo "$total_requests * 0.95" | bc | cut -d. -f1)
    local p99_line=$(echo "$total_requests * 0.99" | bc | cut -d. -f1)
    local p95_time=$(sed -n "${p95_line}p" "$OUTPUT_DIR/sorted_times.txt")
    local p99_time=$(sed -n "${p99_line}p" "$OUTPUT_DIR/sorted_times.txt")
    
    # Generate report
    cat > "$OUTPUT_DIR/load_test_report.txt" << EOF
DotMac Platform Load Test Report
===============================
Date: $(date)
Base URL: $BASE_URL
Concurrent Users: $CONCURRENT_USERS
Requests per User: $REQUESTS_PER_USER
Test Duration: $TEST_DURATION seconds

Results Summary:
- Total Requests: $total_requests
- Successful Requests: $successful_requests
- Failed Requests: $failed_requests
- Success Rate: $success_rate%
- Requests per Second: $requests_per_second
- Average Response Time: ${avg_response_time}ms
- 95th Percentile: ${p95_time}ms
- 99th Percentile: ${p99_time}ms

Performance Assessment:
$([ $(echo "$success_rate >= 95" | bc -l) -eq 1 ] && echo "✅ Success rate is good (≥95%)" || echo "❌ Success rate is low (<95%)")
$([ $(echo "$avg_response_time <= 500" | bc -l) -eq 1 ] && echo "✅ Average response time is good (≤500ms)" || echo "❌ Average response time is high (>500ms)")
$([ $(echo "$p95_time <= 1000" | bc -l) -eq 1 ] && echo "✅ 95th percentile is good (≤1000ms)" || echo "❌ 95th percentile is high (>1000ms)")
$([ $(echo "$requests_per_second >= 10" | bc -l) -eq 1 ] && echo "✅ Throughput is acceptable (≥10 RPS)" || echo "❌ Throughput is low (<10 RPS)")

EOF
    
    # Display report
    cat "$OUTPUT_DIR/load_test_report.txt"
    
    # Create simple CSV summary
    echo "timestamp,total_requests,successful_requests,failed_requests,success_rate,avg_response_time_ms,p95_time_ms,requests_per_second" > "$OUTPUT_DIR/summary.csv"
    echo "$(date -Iseconds),$total_requests,$successful_requests,$failed_requests,$success_rate,$avg_response_time,$p95_time,$requests_per_second" >> "$OUTPUT_DIR/summary.csv"
    
    log "Load test report saved to: $OUTPUT_DIR/load_test_report.txt"
}

# Run system monitoring during test
monitor_system() {
    log "Starting system monitoring..."
    
    # Monitor for test duration
    for ((i=0; i<TEST_DURATION; i+=5)); do
        echo "$(date -Iseconds),$(cat /proc/loadavg | cut -d' ' -f1),$(free | grep Mem: | awk '{printf "%.1f", $3/$2 * 100}'),$(df / | tail -1 | awk '{print $5}' | sed 's/%//')" >> "$OUTPUT_DIR/system_metrics.csv"
        sleep 5
    done &
    
    echo "timestamp,load_avg,memory_percent,disk_percent" > "$OUTPUT_DIR/system_metrics_header.csv"
    cat "$OUTPUT_DIR/system_metrics_header.csv" "$OUTPUT_DIR/system_metrics.csv" > "$OUTPUT_DIR/system_metrics_final.csv"
}

# Main load test function
run_load_test() {
    local endpoints=("/health" "/api/v1/customers" "/api/v1/services")
    
    log "Starting load test with $CONCURRENT_USERS concurrent users"
    log "Each user will make $REQUESTS_PER_USER requests"
    log "Total expected requests: $((CONCURRENT_USERS * REQUESTS_PER_USER))"
    
    # Start system monitoring
    monitor_system &
    monitor_pid=$!
    
    # Start load test
    local pids=()
    
    for ((user=1; user<=CONCURRENT_USERS; user++)); do
        # Each user tests a different endpoint (round robin)
        endpoint=${endpoints[$((user % ${#endpoints[@]}))]}
        
        run_curl_load_test "$endpoint" "$user" "$REQUESTS_PER_USER" &
        pids+=($!)
    done
    
    # Wait for all users to complete
    for pid in "${pids[@]}"; do
        wait "$pid"
    done
    
    # Stop system monitoring
    kill $monitor_pid 2>/dev/null || true
    wait $monitor_pid 2>/dev/null || true
    
    log "Load test completed"
    
    # Generate report
    generate_report
}

# Database stress test
test_database_load() {
    log "Testing database load..."
    
    # Simple database connection test
    if command -v psql >/dev/null 2>&1; then
        export PGPASSWORD="${POSTGRES_PASSWORD:-}"
        
        for ((i=1; i<=100; i++)); do
            echo "SELECT COUNT(*) FROM pg_stat_activity;" | psql -h "${POSTGRES_HOST:-localhost}" -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-dotmac_db}" -t >/dev/null 2>&1
            if [[ $? -eq 0 ]]; then
                echo "." >> "$OUTPUT_DIR/db_test_success.txt"
            else
                echo "x" >> "$OUTPUT_DIR/db_test_errors.txt"
            fi
        done
        
        local success_count=$(wc -c < "$OUTPUT_DIR/db_test_success.txt" 2>/dev/null || echo 0)
        local error_count=$(wc -c < "$OUTPUT_DIR/db_test_errors.txt" 2>/dev/null || echo 0)
        
        log "Database test: $success_count successful, $error_count failed"
    else
        log "psql not available, skipping database load test"
    fi
}

# Redis stress test  
test_redis_load() {
    log "Testing Redis load..."
    
    if command -v redis-cli >/dev/null 2>&1; then
        local redis_args=""
        if [[ -n "${REDIS_PASSWORD:-}" ]]; then
            redis_args="-a $REDIS_PASSWORD"
        fi
        
        # Simple Redis test
        for ((i=1; i<=100; i++)); do
            echo "SET test:$i value$i" | redis-cli -h "${REDIS_HOST:-localhost}" -p "${REDIS_PORT:-6379}" $redis_args >/dev/null 2>&1
            if [[ $? -eq 0 ]]; then
                echo "." >> "$OUTPUT_DIR/redis_test_success.txt"
            else
                echo "x" >> "$OUTPUT_DIR/redis_test_errors.txt"
            fi
        done
        
        # Cleanup
        redis-cli -h "${REDIS_HOST:-localhost}" -p "${REDIS_PORT:-6379}" $redis_args DEL "test:*" >/dev/null 2>&1 || true
        
        local success_count=$(wc -c < "$OUTPUT_DIR/redis_test_success.txt" 2>/dev/null || echo 0)
        local error_count=$(wc -c < "$OUTPUT_DIR/redis_test_errors.txt" 2>/dev/null || echo 0)
        
        log "Redis test: $success_count successful, $error_count failed"
    else
        log "redis-cli not available, skipping Redis load test"
    fi
}

# Cleanup function
cleanup() {
    # Kill any remaining background processes
    jobs -p | xargs -r kill 2>/dev/null || true
    
    # Clean up temp files
    rm -f "$OUTPUT_DIR"/user_*_results.txt "$OUTPUT_DIR"/system_metrics.csv 2>/dev/null || true
    rm -f "$OUTPUT_DIR"/db_test_*.txt "$OUTPUT_DIR"/redis_test_*.txt 2>/dev/null || true
    rm -f "$OUTPUT_DIR"/sorted_times.txt "$OUTPUT_DIR"/system_metrics_header.csv 2>/dev/null || true
    
    log "Cleanup completed"
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Main execution
case "${1:-load-test}" in
    load-test)
        check_services
        run_load_test
        ;;
    db-test)
        test_database_load
        ;;
    redis-test)
        test_redis_load
        ;;
    quick-test)
        CONCURRENT_USERS=5
        REQUESTS_PER_USER=10
        TEST_DURATION=30
        check_services
        run_load_test
        ;;
    *)
        echo "Usage: $0 {load-test|db-test|redis-test|quick-test}"
        echo
        echo "Commands:"
        echo "  load-test   - Full load test (default)"
        echo "  db-test     - Database load test only"
        echo "  redis-test  - Redis load test only"
        echo "  quick-test  - Quick load test (5 users, 10 requests, 30s)"
        echo
        echo "Environment variables:"
        echo "  BASE_URL=$BASE_URL"
        echo "  CONCURRENT_USERS=$CONCURRENT_USERS"
        echo "  REQUESTS_PER_USER=$REQUESTS_PER_USER"
        echo "  TEST_DURATION=$TEST_DURATION"
        exit 1
        ;;
esac
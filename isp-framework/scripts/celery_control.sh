#!/bin/bash

# DotMac ISP Framework - Celery Control Script
# Usage: ./scripts/celery_control.sh [start|stop|restart|status|logs]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Set Python path
export PYTHONPATH=src

# PID file locations
WORKER_PID_FILE="/tmp/celery_worker.pid"
BEAT_PID_FILE="/tmp/celery_beat.pid"

start_worker() {
    echo "Starting Celery worker..."
    nohup celery -A dotmac_isp.core.celery_app worker --loglevel=info --pool=solo \
        --pidfile="$WORKER_PID_FILE" \
        --logfile="/tmp/celery_worker.log" \
        --detach
    
    if [ $? -eq 0 ]; then
        echo "✅ Celery worker started successfully"
    else
        echo "❌ Failed to start Celery worker"
        return 1
    fi
}

start_beat() {
    echo "Starting Celery beat scheduler..."
    nohup celery -A dotmac_isp.core.celery_app beat --loglevel=info \
        --pidfile="$BEAT_PID_FILE" \
        --logfile="/tmp/celery_beat.log" \
        --detach
    
    if [ $? -eq 0 ]; then
        echo "✅ Celery beat scheduler started successfully"
    else
        echo "❌ Failed to start Celery beat scheduler"
        return 1
    fi
}

stop_worker() {
    if [ -f "$WORKER_PID_FILE" ]; then
        echo "Stopping Celery worker..."
        celery -A dotmac_isp.core.celery_app control shutdown
        rm -f "$WORKER_PID_FILE"
        echo "✅ Celery worker stopped"
    else
        echo "⚠️  Celery worker PID file not found"
    fi
}

stop_beat() {
    if [ -f "$BEAT_PID_FILE" ]; then
        echo "Stopping Celery beat scheduler..."
        PID=$(cat "$BEAT_PID_FILE")
        kill "$PID" 2>/dev/null
        rm -f "$BEAT_PID_FILE"
        echo "✅ Celery beat scheduler stopped"
    else
        echo "⚠️  Celery beat scheduler PID file not found"
    fi
}

show_status() {
    echo "=== Celery Status ==="
    
    # Check worker status
    if [ -f "$WORKER_PID_FILE" ]; then
        PID=$(cat "$WORKER_PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "✅ Celery Worker: Running (PID: $PID)"
        else
            echo "❌ Celery Worker: Dead (stale PID file)"
            rm -f "$WORKER_PID_FILE"
        fi
    else
        echo "❌ Celery Worker: Not running"
    fi
    
    # Check beat status  
    if [ -f "$BEAT_PID_FILE" ]; then
        PID=$(cat "$BEAT_PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "✅ Celery Beat: Running (PID: $PID)"
        else
            echo "❌ Celery Beat: Dead (stale PID file)"
            rm -f "$BEAT_PID_FILE"
        fi
    else
        echo "❌ Celery Beat: Not running"
    fi
    
    # Show worker stats if available
    echo ""
    echo "=== Worker Statistics ==="
    celery -A dotmac_isp.core.celery_app inspect stats 2>/dev/null || echo "No workers available for inspection"
}

show_logs() {
    echo "=== Recent Celery Worker Logs ==="
    if [ -f "/tmp/celery_worker.log" ]; then
        tail -n 20 /tmp/celery_worker.log
    else
        echo "No worker log file found"
    fi
    
    echo ""
    echo "=== Recent Celery Beat Logs ==="
    if [ -f "/tmp/celery_beat.log" ]; then
        tail -n 20 /tmp/celery_beat.log
    else
        echo "No beat log file found"
    fi
}

test_celery() {
    echo "=== Testing Celery Task Execution ==="
    python3 -c "
from dotmac_isp.core.celery_app import celery_app
from dotmac_isp.core.tasks import health_check

print('Submitting health check task...')
result = health_check.delay()
print(f'Task ID: {result.id}')

try:
    task_result = result.get(timeout=10)
    print('✅ Task completed successfully:')
    print(f'   Status: {task_result.get(\"status\")}')
    print(f'   Redis: {task_result.get(\"redis\")}')
except Exception as e:
    print(f'❌ Task failed: {e}')
"
}

case "$1" in
    start)
        start_worker
        sleep 2
        start_beat
        ;;
    stop)
        stop_worker
        stop_beat
        ;;
    restart)
        stop_worker
        stop_beat
        sleep 2
        start_worker
        sleep 2
        start_beat
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    test)
        test_celery
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|test}"
        echo ""
        echo "Commands:"
        echo "  start    - Start Celery worker and beat scheduler"
        echo "  stop     - Stop all Celery processes"
        echo "  restart  - Restart all Celery processes"
        echo "  status   - Show status of Celery processes"
        echo "  logs     - Show recent log entries"
        echo "  test     - Test task execution"
        exit 1
        ;;
esac
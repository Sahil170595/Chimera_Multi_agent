#!/bin/bash
# Linux/Mac cron scheduler for Muse Protocol agents

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_EXE="$PROJECT_ROOT/.venv/bin/python"
MUSE_CLI="apps.muse_cli"

# Load environment
if [ -f "$PROJECT_ROOT/env.local" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/env.local" | xargs)
fi

# Crontab entries
CRON_ENTRIES="
# Muse Protocol Agent Scheduler
*/5 * * * * cd $PROJECT_ROOT && $PYTHON_EXE -m $MUSE_CLI ingest >> /tmp/muse_ingest.log 2>&1
*/15 * * * * cd $PROJECT_ROOT && $PYTHON_EXE -m $MUSE_CLI collect -h 24 >> /tmp/muse_collect.log 2>&1
*/10 * * * * cd $PROJECT_ROOT && $PYTHON_EXE -m $MUSE_CLI watcher -h 1 >> /tmp/muse_watcher.log 2>&1
0 * * * * cd $PROJECT_ROOT && $PYTHON_EXE -m $MUSE_CLI council >> /tmp/muse_council.log 2>&1
0 */2 * * * cd $PROJECT_ROOT && $PYTHON_EXE -m $MUSE_CLI publish >> /tmp/muse_publish.log 2>&1
0 */4 * * * cd $PROJECT_ROOT && $PYTHON_EXE -m $MUSE_CLI translate -l de,zh,hi >> /tmp/muse_translate.log 2>&1
"

function install_cron() {
    echo "Installing Muse Protocol cron jobs..."
    
    # Backup existing crontab
    crontab -l > /tmp/crontab.backup 2>/dev/null || true
    
    # Remove old Muse entries
    crontab -l 2>/dev/null | grep -v "Muse Protocol" | grep -v "muse_" > /tmp/crontab.new || true
    
    # Add new entries
    echo "$CRON_ENTRIES" >> /tmp/crontab.new
    
    # Install
    crontab /tmp/crontab.new
    
    echo "✅ Cron jobs installed"
    echo "Run 'crontab -l' to verify"
}

function uninstall_cron() {
    echo "Uninstalling Muse Protocol cron jobs..."
    
    # Remove Muse entries
    crontab -l 2>/dev/null | grep -v "Muse Protocol" | grep -v "muse_" > /tmp/crontab.new || true
    
    # Install cleaned crontab
    crontab /tmp/crontab.new
    
    echo "✅ Cron jobs uninstalled"
}

function show_status() {
    echo "Muse Protocol Cron Jobs:"
    echo ""
    crontab -l 2>/dev/null | grep -A 10 "Muse Protocol" || echo "No cron jobs installed"
    echo ""
    echo "Recent logs:"
    echo "  Ingestor:   tail -f /tmp/muse_ingest.log"
    echo "  Collector:  tail -f /tmp/muse_collect.log"
    echo "  Watcher:    tail -f /tmp/muse_watcher.log"
    echo "  Council:    tail -f /tmp/muse_council.log"
    echo "  Publisher:  tail -f /tmp/muse_publish.log"
    echo "  Translator: tail -f /tmp/muse_translate.log"
}

# Main
case "$1" in
    install)
        install_cron
        ;;
    uninstall)
        uninstall_cron
        ;;
    status)
        show_status
        ;;
    *)
        echo "Muse Protocol Cron Scheduler"
        echo ""
        echo "Usage:"
        echo "  $0 install    Install cron jobs"
        echo "  $0 uninstall  Remove cron jobs"
        echo "  $0 status     Show cron status"
        echo ""
        echo "Schedule:"
        echo "  - Ingestor:   Every 5 minutes"
        echo "  - Collector:  Every 15 minutes"
        echo "  - Watcher:    Every 10 minutes"
        echo "  - Council:    Hourly"
        echo "  - Publisher:  Every 2 hours"
        echo "  - Translator: Every 4 hours"
        ;;
esac

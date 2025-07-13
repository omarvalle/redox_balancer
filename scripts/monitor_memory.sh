#!/bin/bash
# Memory watchdog for training

while true; do
    echo "[$(date +%H:%M:%S)] Memory check:"
    free -g | grep Mem | awk '{print "  Used: " $3 "GB / 1488GB (" int($3*100/1488) "%)"}'
    
    # Alert if > 80% used
    USED=$(free -g | grep Mem | awk '{print $3}')
    if [ $USED -gt 1190 ]; then
        echo "  WARNING: Memory usage critical!"
        echo "  Consider reducing actors or killing largest process"
    fi
    
    # Show largest Python processes
    echo "  Top Python processes:"
    ps aux | grep python | grep -v grep | sort -k6 -nr | head -3 | awk '{printf "    PID %s: %.1fGB - %s\n", $2, $6/1048576, substr($0, index($0,$11))}'
    
    echo
    sleep 30
done
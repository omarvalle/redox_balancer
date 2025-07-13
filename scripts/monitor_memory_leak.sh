#!/bin/bash
# Advanced memory leak monitoring for training

LOG_FILE="memory_leak_analysis.log"

echo "=== MEMORY LEAK MONITOR ===" | tee $LOG_FILE
echo "Started: $(date)" | tee -a $LOG_FILE
echo | tee -a $LOG_FILE

while true; do
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    
    # Overall system memory
    echo "[$TIMESTAMP] System Memory:" | tee -a $LOG_FILE
    free -g | grep Mem | tee -a $LOG_FILE
    
    # Ray object store
    echo "Ray Object Store:" | tee -a $LOG_FILE
    ray memory --stats-only 2>/dev/null | head -10 | tee -a $LOG_FILE || echo "Ray not running"
    
    # Top Python processes by memory
    echo "Top Python Processes:" | tee -a $LOG_FILE
    ps aux | grep python | grep -v grep | sort -k6 -nr | head -10 | \
        awk '{printf "  PID %s: %.2fGB RSS, %.1f%%CPU - %s\n", $2, $6/1048576, $3, substr($0, index($0,$11),40)}' | tee -a $LOG_FILE
    
    # Count actor processes
    ACTOR_COUNT=$(ps aux | grep "ray::ActorWorker" | grep -v grep | wc -l)
    echo "Active Ray Actors: $ACTOR_COUNT" | tee -a $LOG_FILE
    
    # Average memory per actor
    if [ $ACTOR_COUNT -gt 0 ]; then
        AVG_MEM=$(ps aux | grep "ray::ActorWorker" | grep -v grep | awk '{sum+=$6} END {printf "%.2f", sum/NR/1048576}')
        echo "Average Memory per Actor: ${AVG_MEM}GB" | tee -a $LOG_FILE
    fi
    
    # Check training log for memory profile entries
    echo "Recent Memory Profiles:" | tee -a $LOG_FILE
    tail -1000 training_resume.log 2>/dev/null | grep "MEMORY_PROFILE" | tail -3 | tee -a $LOG_FILE
    
    # Look for growing object types
    echo "Growing Object Types:" | tee -a $LOG_FILE
    tail -1000 training_resume.log 2>/dev/null | grep "Top growing types" | tail -1 | tee -a $LOG_FILE
    
    echo "----------------------------------------" | tee -a $LOG_FILE
    
    # Alert if memory usage is high
    USED_GB=$(free -g | grep Mem | awk '{print $3}')
    if [ $USED_GB -gt 1200 ]; then
        echo "⚠️  WARNING: Memory usage critical! ${USED_GB}GB used" | tee -a $LOG_FILE
        
        # Log detailed process info
        echo "Detailed Process Memory:" | tee -a $LOG_FILE
        ps aux | grep python | sort -k6 -nr | head -20 >> $LOG_FILE
    fi
    
    sleep 60  # Check every minute
done
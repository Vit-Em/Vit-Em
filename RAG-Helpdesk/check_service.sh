#!/bin/bash

# Check if the service is running
SERVICE_STATUS=$(systemctl is-active fdc-memory-service.service)

if [ "$SERVICE_STATUS" = "active" ]; then
    echo "✅ FDC Memory Bank service is running"
    
    # Check if the API is responding
    if curl -s http://localhost:5000/health | grep -q "healthy"; then
        echo "✅ API is responding and healthy"
    else
        echo "❌ Service is running but API is not responding correctly"
        echo "Try restarting with: sudo systemctl restart fdc-memory-service.service"
    fi
else
    echo "❌ FDC Memory Bank service is not running"
    echo "Start it with: sudo systemctl start fdc-memory-service.service"
fi 
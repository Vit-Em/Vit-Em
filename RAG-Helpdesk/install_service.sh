#!/bin/bash

# Make script executable
chmod +x fdc-memory-api.py

# Copy service file to systemd directory
sudo cp fdc-memory-service.service /etc/systemd/system/

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable fdc-memory-service.service

# Start the service
sudo systemctl start fdc-memory-service.service

# Check status
sudo systemctl status fdc-memory-service.service

echo "Service installation complete. The Memory Bank API is now running as a daemon."
echo "You can check its status anytime with: sudo systemctl status fdc-memory-service.service"
echo "You can stop it with: sudo systemctl stop fdc-memory-service.service"
echo "You can restart it with: sudo systemctl restart fdc-memory-service.service" 
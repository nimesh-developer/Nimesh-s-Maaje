#!/bin/bash
# Moving Trashcan - Automated Setup Script
# Run this on your Raspberry Pi to make the code actually work seamlessly.

echo "Starting Moving Trashcan Setup..."

# Update system
echo "Updating packages..."
sudo apt-get update -y

# Install dependencies
echo "Installing Python and OpenCV dependencies..."
sudo apt-get install python3-pip python3-opencv -y
pip3 install numpy RPi.GPIO

# Make the python script executable
chmod +x trashcan_robot_code.py

# Setup systemd service to run seamlessly on boot
echo "Configuring automatic start on boot..."
SERVICE_FILE="/etc/systemd/system/trashcan.service"

sudo bash -c "cat > $SERVICE_FILE" << EOF
[Unit]
Description=Trashcan Robot Tracker
After=network.target

[Service]
ExecStart=/usr/bin/python3 $(pwd)/trashcan_robot_code.py
WorkingDirectory=$(pwd)
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable trashcan.service
sudo systemctl restart trashcan.service

echo "Setup Complete! The trashcan code is now running and will start automatically on boot."

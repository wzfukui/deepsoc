#!/bin/bash

echo "=== DeepSOC Deployment Check Script ==="
echo "Date: $(date)"
echo "---------------------------------------"

# 1. OS Check
echo "[1] Checking OS Info..."
if [ -f /etc/os-release ]; then
    cat /etc/os-release | grep PRETTY_NAME
else
    echo "Cannot determine OS version"
fi
echo ""

# 2. System Resources
echo "[2] Checking System Resources..."
echo "--- CPU ---"
lscpu | grep "CPU(s):" | head -1
echo "--- Memory ---"
free -h
echo "--- Disk Space ---"
df -h / | grep /
echo ""

# 3. Python Environment
echo "[3] Checking Python Version..."
if command -v python3 &> /dev/null; then
    python3 --version
else
    echo "Python3 not found"
fi
if command -v pip3 &> /dev/null; then
    echo "pip3 is installed"
else
    echo "pip3 not found"
fi
echo ""

# 4. Git
echo "[4] Checking Git..."
if command -v git &> /dev/null; then
    git --version
else
    echo "git not found"
fi
echo ""

# 5. Database (MySQL)
echo "[5] Checking MySQL..."
if systemctl is-active --quiet mysql; then
    echo "MySQL Service: Active"
else
    echo "MySQL Service: Inactive or Not Installed"
fi
# Check port 3306
if ss -tuln | grep -q ":3306"; then
    echo "Port 3306 (MySQL) is in use"
else
    echo "Port 3306 (MySQL) is free"
fi
echo ""

# 6. Message Queue (RabbitMQ)
echo "[6] Checking RabbitMQ..."
if systemctl is-active --quiet rabbitmq-server; then
    echo "RabbitMQ Service: Active"
else
    echo "RabbitMQ Service: Inactive or Not Installed"
fi
# Check port 5672
if ss -tuln | grep -q ":5672"; then
    echo "Port 5672 (RabbitMQ) is in use"
else
    echo "Port 5672 (RabbitMQ) is free"
fi
echo ""

# 7. Network Connectivity
echo "[7] Checking Network..."
if ping -c 1 8.8.8.8 &> /dev/null; then
    echo "Internet connectivity: OK"
else
    echo "Internet connectivity: Failed"
fi
echo ""

# 8. Required Ports Availability
echo "[8] Checking Required Ports for DeepSOC..."
# Assuming DeepSOC uses 5000 by default
if ss -tuln | grep -q ":5000"; then
    echo "Port 5000 (DeepSOC Web) is in use - WARNING"
else
    echo "Port 5000 (DeepSOC Web) is available"
fi

echo "---------------------------------------"
echo "Check Completed."

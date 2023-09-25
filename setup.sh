#!/bin/bash

# Detect OS
OS_NAME=$(uname)

# Update and install for Linux
if [ "$OS_NAME" == "Linux" ]; then
    sudo amazon-linux-extras install epel -y
    sudo yum install -y chromium
    sudo yum install -y Xvfb
    Xvfb :99 & 
    export DISPLAY=:99
    sudo yum install -y python3-pip
    pip3 install selenium bs4 cloudscraper
    CHROMIUM_VERSION=$(chromium-browser --version | awk '{print $2}' | awk -F. '{print $1}')
    wget https://chromedriver.storage.googleapis.com/$CHROMIUM_VERSION.0/chromedriver_linux64.zip
    unzip chromedriver_linux64.zip
    sudo mv chromedriver /usr/local/bin/
    sudo chmod +x /usr/local/bin/chromedriver
elif [ "$OS_NAME" == "Darwin" ]; then # For MacOS
    brew install chromium chromedriver
    pip3 install selenium bs4 cloudscraper
else
    echo "Unsupported OS."
    exit 1
fi

echo "Setup is complete. You can now run your Python script."

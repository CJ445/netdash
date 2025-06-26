#!/bin/bash
# Script to setup and run NetDash

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}NetDash Setup and Run Script${NC}"
echo "------------------------------"

# Check if running as root for sensitive operations
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${YELLOW}Notice: Not running as root. Some features may not work.${NC}"
    echo -e "${YELLOW}Consider using sudo for full functionality.${NC}"
fi

# Check if we're in the project directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Not in the NetDash project directory.${NC}"
    echo "Please run this script from the NetDash project root."
    exit 1
fi

# Setup virtual environment if needed
if [ ! -d "venv" ]; then
    echo -e "${GREEN}Setting up virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -e .

# Generate sample log file for testing
echo -e "${GREEN}Generating sample log file...${NC}"
python tools/generate_sample_log.py

# Run the application
echo -e "${GREEN}Starting NetDash...${NC}"
echo "Press Ctrl+C to exit."
echo "------------------------------"

# Check command line arguments
if [ "$1" == "--component" ] && [ -n "$2" ]; then
    python -m netdash --component "$2" ${@:3}
elif [ "$1" == "--log-file" ] && [ -n "$2" ]; then
    python -m netdash --log-file "$2" ${@:3}
elif [ "$1" == "--rich-only" ]; then
    python -m netdash --rich-only ${@:2}
else
    python -m netdash "$@"
fi

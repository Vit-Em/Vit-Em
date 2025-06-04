#!/bin/bash

# Create a symbolic link in /usr/local/bin
sudo ln -sf "$(pwd)/mb-query" /usr/local/bin/mb-query

echo "Symbolic link created. You can now use 'mb-query' from anywhere."
echo "Example: mb-query query \"What is the project status?\"" 
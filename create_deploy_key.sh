#!/bin/bash

# Constants for frequently used paths
SSH_DIR="$HOME/.ssh"
SSH_CONFIG_FILE="$SSH_DIR/config"

# Function to display usage information
display_usage() {
    echo "Usage: $0 --project_name <project_name>"
    exit 1
}

# Function to check and create SSH key and update SSH config
create_and_update_ssh_keys() {
    local project_name="$1"
    local ssh_key_file="${SSH_DIR}/${project_name}_key"

    if [ -f "$ssh_key_file" ]; then
        echo "Error: SSH key for project '$project_name' already exists at $ssh_key_file."
        exit 1
    fi

    # Generate SSH key
    ssh-keygen -t ed25519 -C "deploy-key-for-${project_name}" -f "$ssh_key_file" -N ""

    # Add SSH config entry
    {
        echo -e "\n# Configuration for ${project_name}"
        echo "Host github-${project_name}"
        echo "    HostName github.com"
        echo "    User git"
        echo "    IdentityFile $ssh_key_file"
        echo "    IdentitiesOnly yes"
    } >> "$SSH_CONFIG_FILE"

    # Output public key and instructions
    echo "Public key for ${project_name}:"
    cat "${ssh_key_file}.pub"
    echo -e "\nAdd this key to your GitHub repository under Settings > Deploy keys."
    echo "Use the alias 'github-${project_name}' to clone the repository."
}

# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --project_name)
            project_name="$2"
            shift 2
            ;;
        *)
            display_usage
            ;;
    esac
done

# Check if project_name is provided
if [ -z "$project_name" ]; then
    display_usage
fi

# Call the function with the provided project name
create_and_update_ssh_keys "$project_name"
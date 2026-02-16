#!/bin/bash

# Initialize an Expo project from the template
# Usage: ./init.sh <project_dir> <app_name> <bundle_id>

PROJECT_DIR=$1
APP_NAME=$2
BUNDLE_ID=$3

if [ -z "$PROJECT_DIR" ] || [ -z "$APP_NAME" ] || [ -z "$BUNDLE_ID" ]; then
    echo "Usage: ./init.sh <project_dir> <app_name> <bundle_id>"
    exit 1
fi

echo "Initializing Expo project: $APP_NAME ($BUNDLE_ID) in $PROJECT_DIR"

# Create project directory
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Create package.json
cat > package.json <<EOF
{
  "name": "$(echo $APP_NAME | tr '[:upper:]' '[:lower:]' | tr ' ' '-')",
  "version": "1.0.0",
  "main": "node_modules/expo/AppEntry.js",
  "scripts": {
    "start": "expo start",
    "android": "expo start --android",
    "ios": "expo start --ios",
    "web": "expo start --web"
  },
  "dependencies": {
    "expo": "~52.0.0",
    "expo-status-bar": "~2.0.0",
    "react": "18.3.1",
    "react-native": "0.76.6",
    "react-native-webview": "13.12.5",
    "expo-notifications": "~0.29.0",
    "expo-device": "~7.0.0",
    "expo-linking": "~7.0.0",
    "expo-constants": "~17.0.0"
  },
  "devDependencies": {
    "@babel/core": "^7.24.0",
    "@types/react": "~18.3.0",
    "typescript": "~5.3.0"
  },
  "private": true
}
EOF

# Copy App.tsx from template
cp /home/ubuntu/auto-deploy-stores/wrapper/template/App.tsx .

# Initialize other config files (babel, tsconfig, etc.)
# These are also handled by the Python CLI's TemplateEngine

echo "Project structure initialized."

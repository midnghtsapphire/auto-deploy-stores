# Auto-Deploy Stores 🚀

A complete, production-ready auto-deploy pipeline that wraps React/Vite web apps into Expo/React Native mobile apps and deploys them to both **Apple App Store** and **Google Play Store**.

Provided by free sources and APIs — **MIDNGHTSAPPHIRE / GlowStar Labs**.

## 🌟 Key Features

- **Universal Wrapper**: Automatically wraps any React/Vite web app into an Expo project using WebView or native components.
- **Cross-Platform**: Supports parallel building and submission to both iOS and Android stores.
- **Secure Vault**: Encrypted storage for Apple API keys, Google service accounts, and signing certificates (glowstarlabs-vault pattern).
- **MCP Server**: Exposes the entire pipeline as Model Context Protocol tools for integration with AI agents and other tools.
- **GitHub Actions**: Reusable CI/CD workflows for automated deployments on push.
- **Production Ready**: Includes comprehensive tests, error handling, and status monitoring.

## 🛠 Tech Stack

- **CLI**: Python (Click, Rich)
- **Wrapper**: Expo SDK 52+, React Native, React Native Web
- **Backend**: FastAPI (MCP Server)
- **CI/CD**: GitHub Actions, EAS Build & Submit
- **Encryption**: Cryptography (Fernet)

## 🚀 Getting Started

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/MIDNGHTSAPPHIRE/auto-deploy-stores.git
cd auto-deploy-stores

# Install the CLI tool
pip install .
```

### 2. Initialize Project

```bash
autodeploy init --name "My Awesome App" --bundle-id "com.mycompany.app" --source "../my-web-app"
```

### 3. Setup Credentials

```bash
autodeploy credentials setup
```

### 4. Deploy

```bash
# Wrap, build, and submit in one command
autodeploy deploy --target both --mode webview
```

## 📦 Project Structure

- `cli/`: Core Python CLI tool.
- `wrapper/`: Expo template and asset generation scripts.
- `vault/`: Encrypted credential storage.
- `mcp_server/`: FastAPI-based MCP server.
- `github_actions/`: Reusable workflow files.
- `tests/`: Comprehensive test suite.

## 🔒 Security

All credentials are stored encrypted using the **Fernet** symmetric encryption. The master key can be provided via the `AUTODEPLOY_MASTER_KEY` environment variable.

## 📝 Attribution

This software is provided by **free sources and APIs**.
Developed and maintained by **MIDNGHTSAPPHIRE / GlowStar Labs**.

## 📄 License

MIT

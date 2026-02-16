"""
Template engine for generating Expo/React Native project files.

Handles creating the project structure and populating templates.
"""

import shutil
from pathlib import Path
from typing import Any


class TemplateEngine:
    """Handles project scaffolding and template rendering."""

    def __init__(self, template_dir: Path | None = None):
        self.template_dir = template_dir or Path("/home/ubuntu/auto-deploy-stores/wrapper/template")

    def create_expo_project(
        self,
        output_path: Path,
        app_name: str,
        bundle_id: str,
        mode: str = "webview",
        features: dict[str, bool] | None = None,
    ) -> None:
        """Create a new Expo project from templates."""
        features = features or {}
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 1. Create directory structure
        (output_path / "assets").mkdir(exist_ok=True)
        (output_path / "src").mkdir(exist_ok=True)
        (output_path / "src/components").mkdir(exist_ok=True)
        (output_path / "src/hooks").mkdir(exist_ok=True)
        
        # 2. Copy static template files
        # Since we are building this from scratch, we'll write the files directly
        self._write_app_entry(output_path, mode, features)
        self._write_babel_config(output_path)
        self._write_tsconfig(output_path)
        self._write_gitignore(output_path)
        self._write_metro_config(output_path)

    def _write_app_entry(self, output_path: Path, mode: str, features: dict[str, bool]) -> None:
        """Write the main App.tsx file."""
        content = """import React, { useEffect } from 'react';
import { StyleSheet, View, SafeAreaView, StatusBar, BackHandler, Platform } from 'react-native';
import { WebView } from 'react-native-webview';
import * as Notifications from 'expo-notifications';
import * as Linking from 'expo-linking';

// Provided by free sources and APIs — MIDNGHTSAPPHIRE / GlowStar Labs

export default function App() {
  const webViewRef = React.useRef<WebView>(null);
  const [url, setUrl] = React.useState('https://glowstarlabs.com'); // Default fallback

  useEffect(() => {
    // Handle back button on Android
    const onBackPress = () => {
      if (webViewRef.current) {
        webViewRef.current.goBack();
        return true;
      }
      return false;
    };

    BackHandler.addEventListener('hardwareBackPress', onBackPress);
    return () => BackHandler.removeEventListener('hardwareBackPress', onBackPress);
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      <WebView
        ref={webViewRef}
        source={{ uri: url }}
        style={styles.webview}
        javaScriptEnabled={true}
        domStorageEnabled={true}
        startInLoadingState={true}
        scalesPageToFit={true}
        allowsBackForwardNavigationGestures={true}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  webview: {
    flex: 1,
  },
});
"""
        (output_path / "App.tsx").write_text(content)

    def _write_babel_config(self, output_path: Path) -> None:
        content = """module.exports = function(api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
  };
};
"""
        (output_path / "babel.config.js").write_text(content)

    def _write_tsconfig(self, output_path: Path) -> None:
        content = """{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true
  }
}
"""
        (output_path / "tsconfig.json").write_text(content)

    def _write_gitignore(self, output_path: Path) -> None:
        content = """node_modules/
.expo/
dist/
npm-debug.*
yarn-debug.*
yarn-error.*
.autodeploy/
artifacts/
credentials/
"""
        (output_path / ".gitignore").write_text(content)

    def _write_metro_config(self, output_path: Path) -> None:
        content = """const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

module.exports = config;
"""
        (output_path / "metro.config.js").write_text(content)

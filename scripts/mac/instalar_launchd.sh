#!/bin/bash
# Instala o duck_mac como serviço do macOS (inicia no boot, reinicia se cair).
# Rode UMA vez no Mac, dentro da pasta do repositório, com as variáveis já exportadas.
set -euo pipefail
: "${DUCK_URL:?exporte DUCK_URL}"; : "${DUCK_SENHA:?exporte DUCK_SENHA}"
DUCK_MAQUINA="${DUCK_MAQUINA:-mac-mini-studio}"
PLIST=~/Library/LaunchAgents/br.com.duckstudios.mac.plist
cat > "$PLIST" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>br.com.duckstudios.mac</string>
  <key>ProgramArguments</key>
  <array><string>/usr/bin/python3</string><string>$(pwd)/scripts/mac/duck_mac.py</string></array>
  <key>EnvironmentVariables</key><dict>
    <key>DUCK_URL</key><string>${DUCK_URL}</string>
    <key>DUCK_USUARIO</key><string>${DUCK_USUARIO:-duck}</string>
    <key>DUCK_SENHA</key><string>${DUCK_SENHA}</string>
    <key>DUCK_MAQUINA</key><string>${DUCK_MAQUINA}</string>
  </dict>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/duck_mac.log</string>
  <key>StandardErrorPath</key><string>/tmp/duck_mac.log</string>
</dict></plist>
XML
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "✓ instalado — logs em /tmp/duck_mac.log; a máquina aparece em /maquinas em ~30s"

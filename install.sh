#!/usr/bin/env bash
set -euo pipefail

APP_ID="focusblock"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${HOME}/.local/share/${APP_ID}"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"

mkdir -p "${TARGET_DIR}" "${BIN_DIR}" "${APP_DIR}"

cp "${SRC_DIR}/focus_block.py" "${TARGET_DIR}/focus_block.py"
cp "${SRC_DIR}/focusblock_icon.png" "${TARGET_DIR}/focusblock_icon.png"
chmod +x "${TARGET_DIR}/focus_block.py"

cat > "${BIN_DIR}/focusblock" <<EOF
#!/usr/bin/env bash
exec python3 "${TARGET_DIR}/focus_block.py"
EOF
chmod +x "${BIN_DIR}/focusblock"

cat > "${APP_DIR}/focusblock.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Focus Block
Comment=Bloqueador de domínios via /etc/hosts
Exec=${BIN_DIR}/focusblock
Icon=${TARGET_DIR}/focusblock_icon.png
Terminal=false
Categories=Utility;
StartupNotify=true
EOF

echo
echo "Instalação concluída."
echo "App: Focus Block"
echo
echo "Se necessário, instale dependências:"
echo "  sudo apt install python3 python3-tk policykit-1"
echo
echo "Abra pelo menu do Linux Mint ou execute:"
echo "  ${BIN_DIR}/focusblock"

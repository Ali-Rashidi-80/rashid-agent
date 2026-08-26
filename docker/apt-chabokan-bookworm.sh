#!/bin/sh
# Point Debian bookworm apt at Chabokan mirror (Iran-friendly builds).
set -eu
rm -f /etc/apt/sources.list.d/debian.sources
cat >/etc/apt/sources.list <<'EOF'
deb [trusted=yes] https://mirror2.chabokan.net/debian bookworm main contrib non-free
deb [trusted=yes] https://mirror2.chabokan.net/debian bookworm-updates main contrib non-free
deb [trusted=yes] https://mirror2.chabokan.net/debian bookworm-security main contrib non-free
EOF
cat >/etc/apt/apt.conf.d/99-mirror-tuning <<'EOF'
Acquire::Check-Valid-Until "false";
Acquire::Retries "3";
Acquire::http::Timeout "120";
EOF

#!/usr/bin/env bash
set -Eeuo pipefail
MODULE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$MODULE_DIR/preinstall-network-tools.sh"
NET_STATE=${TEST_STATE:-$(mktemp -d "${TMPDIR:-/tmp}/network-test.XXXXXX")}
mkdir -p "$NET_STATE"
TRACE="$NET_STATE/trace"
INSTALLED=0; ACTIVE=inactive; ENABLED=disabled; MASKED=0; FAIL_INSTALL=0; LOAD=not-found
dpkg-query() { [[ $INSTALLED == 1 ]] && printf 'install ok installed'; }
configure_repository() { echo "repository $1" >> "$TRACE"; }
apt-cache() { :; }
apt-get() {
  echo "apt $*" >> "$TRACE"
  if [[ $* == *'install -y'* ]]; then
    [[ $FAIL_INSTALL == 0 ]] || return 42
    INSTALLED=1
  fi
}
systemctl() {
  echo "systemctl $*" >> "$TRACE"
  case "$1" in
    is-active) echo "$ACTIVE"; [[ $ACTIVE == active ]];;
    is-enabled) if [[ $MASKED == 1 ]]; then echo masked; return 1; else echo "$ENABLED"; [[ $ENABLED == enabled ]]; fi;;
    show) echo "$LOAD";;
    mask) MASKED=1;;
    unmask) MASKED=0;;
    disable) ENABLED=disabled;;
    stop) ACTIVE=inactive;;
    daemon-reload) :;;
    *) echo "Unexpected systemctl action $*" >&2; return 99;;
  esac
}
tailscale() { [[ $1 == version ]]; echo 'tailscale mock'; }
cloudflared() { [[ $1 == --version ]]; echo 'cloudflared mock'; }
warp-cli() { [[ $1 == --version ]]; echo 'warp mock'; }

if [[ ${1:-} == failure-child ]]; then
  FAIL_INSTALL=1
  install_dormant cloudflare-warp warp-svc.service warp-cli
  exit 99
fi
if [[ ${1:-} == custom-child ]]; then
  LOAD=loaded
  install_dormant tailscale tailscaled.service tailscale
  exit 99
fi

for row in 'tailscale tailscaled.service tailscale' 'cloudflared cloudflared.service cloudflared' 'cloudflare-warp warp-svc.service warp-cli'; do
  read -r pkg svc cli <<< "$row"
  INSTALLED=0; ACTIVE=inactive; ENABLED=disabled; MASKED=0; LOAD=not-found
  : > "$TRACE"
  install_dormant "$pkg" "$svc" "$cli"
  [[ $INSTALLED == 1 && $ACTIVE == inactive && $ENABLED == disabled && $MASKED == 0 ]]
  [[ ! -f $NET_STATE/pending-$pkg ]]
  grep -q "systemctl mask $svc" "$TRACE"
  grep -q "systemctl disable $svc" "$TRACE"
  ! grep -Eq 'systemctl (start|enable|restart)|tailscale up|warp-cli connect' "$TRACE"
  echo "PASS new package stays dormant: $pkg"

  INSTALLED=1; ACTIVE=active; ENABLED=enabled; MASKED=0; LOAD=loaded
  : > "$TRACE"
  install_dormant "$pkg" "$svc" "$cli"
  [[ $ACTIVE == active && $ENABLED == enabled && $MASKED == 0 ]]
  ! grep -Eq '^apt |systemctl (mask|unmask|stop|disable|start|enable|restart)' "$TRACE"
  echo "PASS existing service state preserved: $pkg"
done

INSTALLED=1; ACTIVE=inactive; ENABLED=disabled; MASKED=1; LOAD=masked
: > "$TRACE"
install_dormant tailscale tailscaled.service tailscale
[[ $MASKED == 1 && $ACTIVE == inactive ]]
! grep -Eq 'systemctl (mask|unmask|stop|disable)' "$TRACE"
echo 'PASS an existing user mask is preserved'

INSTALLED=1; ACTIVE=inactive; ENABLED=enabled; MASKED=1; LOAD=masked
touch "$NET_STATE/pending-tailscale"
: > "$TRACE"
install_dormant tailscale tailscaled.service tailscale
[[ $ACTIVE == inactive && $ENABLED == disabled && $MASKED == 0 && ! -f $NET_STATE/pending-tailscale ]]
echo 'PASS owned pending installation resumes without enrollment'

FAIL_STATE=$(mktemp -d "${TMPDIR:-/tmp}/network-failure-test.XXXXXX")
set +e
TEST_STATE="$FAIL_STATE" bash "$0" failure-child >/dev/null 2>&1
status=$?
set -e
[[ $status == 42 && -f $FAIL_STATE/pending-cloudflare-warp ]]
grep -q 'systemctl mask warp-svc.service' "$FAIL_STATE/trace"
! grep -q 'systemctl unmask' "$FAIL_STATE/trace"
echo 'PASS failed install retains its mask and pending marker'
CUSTOM_STATE=$(mktemp -d "${TMPDIR:-/tmp}/network-custom-test.XXXXXX")
set +e
TEST_STATE="$CUSTOM_STATE" bash "$0" custom-child >/dev/null 2>&1
status=$?
set -e
[[ $status == 1 && ! -f $CUSTOM_STATE/pending-tailscale ]]
! grep -Eq '^apt |systemctl (mask|unmask|stop|disable)' "$CUSTOM_STATE/trace"
echo 'PASS an unknown custom service is not taken over'
echo 'All ten network-module lifecycle cases passed.'

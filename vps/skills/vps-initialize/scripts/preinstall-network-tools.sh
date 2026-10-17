#!/usr/bin/env bash
# Install-only: no enrollment, tunnels, exit-node selection, DNS or route changes.
set -Eeuo pipefail
umask 077

fetch() {
  curl --fail --location --silent --show-error --retry 4 --connect-timeout 20 --max-time 120 --proto '=https' --tlsv1.2 "$1" -o "$2.part"
  mv -f "$2.part" "$2"
}

configure_repository() {
  local package=$1
  install -d -m 755 /usr/share/keyrings
  case "$package" in
    tailscale)
      fetch "https://pkgs.tailscale.com/stable/$ID/$VERSION_CODENAME.noarmor.gpg" "$NET_STATE/tailscale.gpg"
      fetch "https://pkgs.tailscale.com/stable/$ID/$VERSION_CODENAME.list" "$NET_STATE/tailscale.list"
      grep -Eq '^deb .*signed-by=/usr/share/keyrings/tailscale-archive-keyring.gpg.*https://pkgs.tailscale.com/stable/' "$NET_STATE/tailscale.list"
      install -m 644 "$NET_STATE/tailscale.gpg" /usr/share/keyrings/tailscale-archive-keyring.gpg
      install -m 644 "$NET_STATE/tailscale.list" /etc/apt/sources.list.d/vps-bootstrap-tailscale.list
      ;;
    cloudflared)
      fetch https://pkg.cloudflare.com/cloudflare-main.gpg "$NET_STATE/cloudflare-main.gpg"
      install -m 644 "$NET_STATE/cloudflare-main.gpg" /usr/share/keyrings/cloudflare-main.gpg
      printf '%s\n' 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' > /etc/apt/sources.list.d/vps-bootstrap-cloudflared.list
      chmod 644 /etc/apt/sources.list.d/vps-bootstrap-cloudflared.list
      ;;
    cloudflare-warp)
      fetch https://pkg.cloudflareclient.com/pubkey.gpg "$NET_STATE/cloudflare-warp.asc"
      gpg --batch --yes --dearmor --output "$NET_STATE/cloudflare-warp.gpg" "$NET_STATE/cloudflare-warp.asc"
      install -m 644 "$NET_STATE/cloudflare-warp.gpg" /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
      printf 'deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ %s main\n' "$VERSION_CODENAME" > /etc/apt/sources.list.d/vps-bootstrap-cloudflare-warp.list
      chmod 644 /etc/apt/sources.list.d/vps-bootstrap-cloudflare-warp.list
      ;;
  esac
}

installed() { [[ $(dpkg-query -W -f='${Status}' "$1" 2>/dev/null || true) == 'install ok installed' ]]; }
service_state() {
  SERVICE_ACTIVE=$(systemctl is-active "$1" 2>/dev/null || true)
  SERVICE_ENABLED=$(systemctl is-enabled "$1" 2>/dev/null || true)
}

install_dormant() {
  local package=$1 service=$2 cli=$3
  local pending="$NET_STATE/pending-$package" before_active before_enabled disposition
  service_state "$service"
  before_active=$SERVICE_ACTIVE; before_enabled=$SERVICE_ENABLED
  if installed "$package" && [[ ! -f $pending ]]; then
    disposition=existing-preserved
  else
    if [[ ! -f $pending ]]; then
      # A package name alone is not permission to take over a custom service.
      [[ $(systemctl show -p LoadState --value "$service") == not-found ]] || {
        echo "$service already exists outside the expected package; inspect before installing" >&2; return 1;
      }
      touch "$pending"
    fi
    # Persistent masking also prevents an interrupted installation from starting on reboot.
    # The marker permits a later run to finish only this script's own pending install.
    systemctl mask "$service"
    if ! installed "$package"; then
      configure_repository "$package"
      apt-get -o DPkg::Lock::Timeout=180 update
      apt-cache show "$package" >/dev/null
      apt-get -o DPkg::Lock::Timeout=180 install -y "$package"
    fi
    systemctl daemon-reload
    # Some packages (cloudflared) have no service until explicitly configured.
    systemctl stop "$service" >/dev/null 2>&1 || true
    systemctl disable "$service" >/dev/null 2>&1 || true
    systemctl unmask "$service"
    # Some systemctl versions cannot disable a masked unit; repeat after unmasking.
    systemctl disable "$service" >/dev/null 2>&1 || true
    service_state "$service"
    if [[ $SERVICE_ACTIVE == active || $SERVICE_ACTIVE == activating || $SERVICE_ENABLED == enabled || $SERVICE_ENABLED == enabled-runtime || $SERVICE_ENABLED == linked || $SERVICE_ENABLED == linked-runtime ]]; then
      systemctl mask "$service"
      echo "Could not keep new service dormant: $service; left masked for inspection" >&2
      return 1
    fi
    rm -f -- "$pending"
    disposition=new-dormant
  fi
  installed "$package"
  command -v "$cli" >/dev/null
  case "$cli" in tailscale) tailscale version;; *) "$cli" --version;; esac
  service_state "$service"
  if [[ $disposition == existing-preserved ]]; then
    [[ $SERVICE_ACTIVE == "$before_active" && $SERVICE_ENABLED == "$before_enabled" ]] || {
      echo "Existing service state changed: $service" >&2; return 1;
    }
  fi
  printf '%s\t%s\t%s\t%s\n' "$package" "$disposition" "$SERVICE_ACTIVE" "$SERVICE_ENABLED" >> "$NET_STATE/verification.tsv"
}

main() {
  [[ $# == 0 ]] || { echo 'This module takes no arguments; install only.' >&2; exit 2; }
  [[ $EUID == 0 && -d /run/systemd/system ]] || { echo 'Root and systemd are required' >&2; exit 1; }
  . /etc/os-release
  [[ $ID == ubuntu || $ID == debian ]]
  [[ ${VERSION_CODENAME:-} =~ ^[a-z]+$ ]] || { echo 'Missing distribution codename'; exit 1; }
  local arch
  arch=$(dpkg --print-architecture)
  [[ $arch == amd64 || $arch == arm64 ]]
  NET_STATE=/var/lib/vps-bootstrap/network-preinstall
  install -d -m 700 "$NET_STATE"
  exec 8>"$NET_STATE/install.lock"
  flock -n 8 || { echo 'Another network preinstall is running'; exit 1; }
  trap 'echo "Network preinstall failed at line $LINENO. Inspect pending markers and service masks in $NET_STATE before retrying." >&2' ERR
  # APT authenticates package indexes and packages with each vendor's signed-by keyring.
  apt-get -o DPkg::Lock::Timeout=180 update
  apt-get -o DPkg::Lock::Timeout=180 install -y ca-certificates curl gnupg
  printf 'package\taction\tservice_active\tservice_enabled\n' > "$NET_STATE/verification.tsv"
  install_dormant tailscale tailscaled.service tailscale
  install_dormant cloudflared cloudflared.service cloudflared
  install_dormant cloudflare-warp warp-svc.service warp-cli
  echo 'NETWORK TOOLS PREINSTALLED. New services are dormant; existing service states were preserved.'
  cat "$NET_STATE/verification.tsv"
  echo 'No account login, Tunnel registration, WARP connection, DNS change or exit-node selection was performed.'
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main "$@"; fi

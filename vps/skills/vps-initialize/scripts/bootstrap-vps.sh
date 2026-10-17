#!/usr/bin/env bash
# Ubuntu/Debian + systemd; run as root. Credentials are generated on the VPS.
# Usage: bash bootstrap-vps.sh --host vps.example.com [--hy-port 443] [--mieru-port 8443]
set -Eeuo pipefail
umask 077
export DEBIAN_FRONTEND=noninteractive
HOST=''; CLIENT_ADDRESS=''; HY_BIND=''; HY_DIRECT_REPLIES=0; HY_PORT=443; MIERU_PORT=8443; NETWORK_PREINSTALL=1
HY_TAG=app/v2.13.0; MIERU_TAG=v3.38.1; NVM_TAG=v0.40.8
while (($#)); do
  case "$1" in
    --host) HOST=${2:?}; shift 2;;
    --client-address) CLIENT_ADDRESS=${2:?}; shift 2;;
    --hy-bind) HY_BIND=${2:?}; shift 2;;
    --hy-direct-replies) HY_DIRECT_REPLIES=1; shift;;
    --hy-port) HY_PORT=${2:?}; shift 2;;
    --mieru-port) MIERU_PORT=${2:?}; shift 2;;
    --skip-network-preinstall) NETWORK_PREINSTALL=0; shift;;
    *) echo "Unknown argument: $1" >&2; exit 2;;
  esac
done
[[ $EUID == 0 ]] || { echo 'Run as root'; exit 1; }
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ $NETWORK_PREINSTALL == 1 && ! -f $SCRIPT_DIR/preinstall-network-tools.sh ]]; then
  echo 'Place preinstall-network-tools.sh beside bootstrap-vps.sh (or explicitly use --skip-network-preinstall).' >&2
  exit 1
fi
# systemd transient jobs may omit HOME; per-user installers require root's real home.
export HOME=/root USER=root LOGNAME=root
[[ $HOST =~ ^[A-Za-z0-9][A-Za-z0-9.:-]*$ ]] || { echo '--host requires a domain or unbracketed IP'; exit 2; }
[[ -z $CLIENT_ADDRESS || $CLIENT_ADDRESS =~ ^[A-Za-z0-9][A-Za-z0-9.:-]*$ ]] || { echo 'Invalid --client-address'; exit 2; }
for p in "$HY_PORT" "$MIERU_PORT"; do
  [[ $p =~ ^[0-9]{1,5}$ ]] && ((10#$p >= 1025 && 10#$p <= 65535 || 10#$p == 443)) || { echo 'Invalid port'; exit 2; }
done
[[ -d /run/systemd/system ]] || { echo 'systemd is required'; exit 1; }
. /etc/os-release
[[ $ID == ubuntu || $ID == debian ]] || { echo 'Only Ubuntu/Debian supported'; exit 1; }
ARCH=$(dpkg --print-architecture)
[[ $ARCH == amd64 || $ARCH == arm64 ]] || { echo 'Only amd64/arm64 supported'; exit 1; }
STATE=/var/lib/vps-bootstrap
install -d -m 700 "$STATE" "$STATE/backups" "$STATE/downloads" "$STATE/clients"
exec 9>"$STATE/install.lock"
flock -n 9 || { echo 'Another bootstrap is running'; exit 1; }
LOG="$STATE/install-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1
trap 'r=$?; echo "FAILED at line $LINENO (exit $r). Log: $LOG"; exit "$r"' ERR
echo "Bootstrap start: $(date -Is), $HOST, $ARCH"
backup() { [[ ! -e $1 ]] || cp -a -- "$1" "$STATE/backups/$(basename "$1").$(date +%s%N)"; }
download() { curl --fail --location --silent --show-error --retry 4 --retry-delay 3 --connect-timeout 20 --max-time 900 --proto '=https' --tlsv1.2 "$1" -o "$2.part"; mv -f "$2.part" "$2"; }
asset() {
  local repo=$1 tag=$2 name=$3 dest=$4 meta="$STATE/downloads/release.json"
  download "https://api.github.com/repos/$repo/releases/tags/${tag//\//%2F}" "$meta"
  mapfile -t fields < <(python3 - "$meta" "$name" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); a=next(a for a in d['assets'] if a['name']==sys.argv[2])
assert a.get('digest','').startswith('sha256:'), 'Official SHA256 digest unavailable'
print(a['browser_download_url']); print(a['digest'][7:])
PY
  )
  [[ ${#fields[@]} == 2 && ${fields[1]} =~ ^[a-f0-9]{64}$ ]]
  if [[ ! -f $dest ]] || ! printf '%s  %s\n' "${fields[1]}" "$dest" | sha256sum -c - >/dev/null 2>&1; then
    download "${fields[0]}" "$dest"
  fi
  printf '%s  %s\n' "${fields[1]}" "$dest" | sha256sum -c -
}
if [[ ! -f $STATE/settings.json ]]; then
  # Refuse to take over services configured by somebody else.
  if command -v hysteria >/dev/null || command -v mita >/dev/null || [[ -e /etc/hysteria/config.yaml || -e /etc/hysteria/config.json ]]; then
    echo 'Existing proxy installation detected. Inspect/migrate it before bootstrapping.'; exit 1
  fi
  for spec in "udp:$HY_PORT" "tcp:$MIERU_PORT"; do
    proto=${spec%%:*}; port=${spec##*:}
    if [[ $proto == tcp ]]; then occupied=$(ss -H -lnt "sport = :$port"); else occupied=$(ss -H -lnu "sport = :$port"); fi
    [[ -z $occupied ]] || { echo "$spec is already in use"; exit 1; }
  done
fi
apt-get -o DPkg::Lock::Timeout=180 update
apt-get -o DPkg::Lock::Timeout=180 install -y ca-certificates curl git build-essential pkg-config libssl-dev python3 openssl chrony xz-utils unzip
if [[ $NETWORK_PREINSTALL == 1 ]]; then
  bash "$SCRIPT_DIR/preinstall-network-tools.sh"
fi
# Small VPS protection. Never resize or replace an existing swap file.
if (( $(awk '/MemTotal/{print $2}' /proc/meminfo) < 2097152 )) && [[ $(swapon --noheadings | wc -l) == 0 ]]; then
  SWAP=/var/swap-vps-bootstrap
  if [[ ! -e $SWAP ]]; then
    (( $(df -Pk /var | awk 'NR==2{print $4}') > 3145728 )) || { echo 'Not enough disk for swap'; exit 1; }
    fallocate -l 2G "$SWAP"
    chmod 600 "$SWAP"; mkswap "$SWAP"
  fi
  [[ -f $SWAP && ! -L $SWAP && $(stat -c %a "$SWAP") == 600 ]]
  swapon "$SWAP"
  if ! grep -q '^/var/swap-vps-bootstrap ' /etc/fstab; then
    backup /etc/fstab
    echo '/var/swap-vps-bootstrap none swap sw 0 0' >> /etc/fstab
  fi
fi
# Keep existing vendor sources and add public fallback sources.
if ! grep -q '# vps-bootstrap time sources' /etc/chrony/chrony.conf; then
  backup /etc/chrony/chrony.conf
  cat >> /etc/chrony/chrony.conf <<'EOF'

# vps-bootstrap time sources
server time.cloudflare.com iburst
pool pool.ntp.org iburst maxsources 3
EOF
  systemctl restart chrony
fi
systemctl enable --now chrony
chronyc online || true
if [[ ! -f $STATE/settings.json ]]; then
  python3 - "$STATE/settings.json" "$HOST" "$HY_PORT" "$MIERU_PORT" <<'PY'
import json,secrets,sys
json.dump(dict(host=sys.argv[2],hy_port=int(sys.argv[3]),mieru_port=int(sys.argv[4]),hy_password=secrets.token_hex(24),mieru_user='vps',mieru_password=secrets.token_hex(24)),open(sys.argv[1],'w'),indent=2)
PY
fi
python3 - "$STATE/settings.json" "$HOST" "$HY_PORT" "$MIERU_PORT" "$CLIENT_ADDRESS" "$HY_BIND" "$HY_DIRECT_REPLIES" <<'PY'
import json,sys,secrets,ipaddress,subprocess
d=json.load(open(sys.argv[1])); assert (d['host'],d['hy_port'],d['mieru_port'])==(sys.argv[2],int(sys.argv[3]),int(sys.argv[4])), 'Saved settings differ; explicit migration required'
d['client_address']=sys.argv[5] or d.get('client_address',d['host'])
d['hy_bind']=sys.argv[6] or d.get('hy_bind','')
d['hy_direct_replies']=bool(int(sys.argv[7])) or d.get('hy_direct_replies',False)
assert not d['hy_direct_replies'] or d['hy_bind'], '--hy-direct-replies requires --hy-bind'
if d['hy_bind']:
    ipaddress.ip_address(d['hy_bind'])
    addrs=json.loads(subprocess.check_output(['ip','-j','address','show']))
    assert any(a['local']==d['hy_bind'] for i in addrs for a in i.get('addr_info',[])), '--hy-bind must be a local interface IP'
d.setdefault('hy_obfs_password',secrets.token_hex(24))
json.dump(d,open(sys.argv[1],'w'),indent=2)
PY

echo 'Installing Hysteria2'
if [[ ! -f $STATE/hysteria-installed ]]; then
  asset apernet/hysteria "$HY_TAG" "hysteria-linux-$ARCH" "$STATE/downloads/hysteria"
  install -m 755 "$STATE/downloads/hysteria" /usr/local/bin/hysteria
  echo "$HY_TAG" > "$STATE/hysteria-installed"
fi
id hysteria >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin hysteria
install -d -m 750 -o root -g hysteria /etc/hysteria
if [[ ! -f /etc/hysteria/server.crt ]]; then
  openssl req -x509 -nodes -newkey ec -pkeyopt ec_paramgen_curve:P-256 -days 3650 -subj "/CN=$HOST" -keyout /etc/hysteria/server.key -out /etc/hysteria/server.crt
fi
if [[ ! -f /etc/hysteria/config.json ]]; then
  python3 - "$STATE/settings.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
json.dump(dict(listen=':'+str(d['hy_port']),tls=dict(cert='/etc/hysteria/server.crt',key='/etc/hysteria/server.key'),auth=dict(type='password',password=d['hy_password'])),open('/etc/hysteria/config.json','w'),indent=2)
PY
fi
HY_CONFIG_UPDATED=$(python3 - "$STATE/settings.json" <<'PY'
import json,sys,shutil,time
d=json.load(open(sys.argv[1])); p='/etc/hysteria/config.json'; c=json.load(open(p))
obfs=dict(type='salamander',salamander=dict(password=d['hy_obfs_password']))
assert 'obfs' not in c or c['obfs']==obfs, 'Existing obfuscation setting differs'
bind=d.get('hy_bind',''); listen=(f'[{bind}]' if ':' in bind else bind)+':'+str(d['hy_port'])
changed='obfs' not in c or c.get('listen')!=listen
if changed:
    shutil.copy2(p,'/var/lib/vps-bootstrap/backups/hysteria-config.'+str(time.time_ns())+'.json')
    c['obfs']=obfs; c['listen']=listen; json.dump(c,open(p,'w'),indent=2)
print(int(changed))
PY
)
chown root:hysteria /etc/hysteria/{server.crt,server.key,config.json}
chmod 640 /etc/hysteria/{server.crt,server.key,config.json}
if python3 - "$STATE/settings.json" <<'PY'
import json,sys
sys.exit(0 if json.load(open(sys.argv[1])).get('hy_direct_replies') else 1)
PY
then
  python3 - "$STATE/settings.json" "$STATE/hy-routing.py" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); family='-6' if ':' in d['hy_bind'] else '-4'
args=[family,'rule','add','priority','4991','from',d['hy_bind'],'ipproto','udp','sport',str(d['hy_port']),'lookup','main']
code='''#!/usr/bin/python3
import subprocess,json
family=FAMILY
rules=json.loads(subprocess.check_output(['ip',family,'-j','rule','show']))
same=[r for r in rules if r.get('priority')==4991]
if same:
    assert len(same)==1 and same[0].get('src')==SOURCE and same[0].get('ipproto')=='udp' and same[0].get('sport')==PORT and same[0].get('table')=='main', 'Routing priority 4991 is already used by another rule'
else:
    subprocess.check_call(['ip']+ARGS)
'''
code=code.replace('FAMILY',repr(family)).replace('SOURCE',repr(d['hy_bind'])).replace('PORT',repr(d['hy_port'])).replace('ARGS',repr(args))
open(sys.argv[2],'w').write(code)
PY
  chmod 700 "$STATE/hy-routing.py"
  if [[ ! -f /etc/systemd/system/vps-hysteria-routing.service ]]; then
    cat > /etc/systemd/system/vps-hysteria-routing.service <<'EOF'
[Unit]
Description=Direct public Hysteria UDP replies with policy routing
After=network-online.target
Wants=network-online.target
Before=hysteria-server.service
[Service]
Type=oneshot
ExecStart=/var/lib/vps-bootstrap/hy-routing.py
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
EOF
  fi
  systemctl daemon-reload
  systemctl enable --now vps-hysteria-routing
fi
if [[ ! -f /etc/systemd/system/hysteria-server.service ]]; then
  cat > /etc/systemd/system/hysteria-server.service <<'EOF'
[Unit]
Description=Hysteria2 proxy server (vps-bootstrap)
After=network-online.target
Wants=network-online.target
[Service]
User=hysteria
Group=hysteria
ExecStart=/usr/local/bin/hysteria server -c /etc/hysteria/config.json
Restart=on-failure
RestartSec=5
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
LimitNOFILE=65536
[Install]
WantedBy=multi-user.target
EOF
fi
systemctl daemon-reload
systemctl enable --now hysteria-server
if [[ $HY_CONFIG_UPDATED == 1 ]]; then systemctl restart hysteria-server; fi

echo 'Installing mieru server and native client'
MV=${MIERU_TAG#v}
if [[ ! -f $STATE/mieru-installed ]]; then
  asset enfein/mieru "$MIERU_TAG" "mita_${MV}_${ARCH}.deb" "$STATE/downloads/mita.deb"
  dpkg -i "$STATE/downloads/mita.deb"
  asset enfein/mieru "$MIERU_TAG" "mieru_${MV}_${ARCH}.deb" "$STATE/downloads/mieru.deb"
  dpkg -i "$STATE/downloads/mieru.deb"
  echo "$MIERU_TAG" > "$STATE/mieru-installed"
fi
systemctl enable --now mita
for i in {1..20}; do mita status >/dev/null 2>&1 && break; sleep 1; done
if [[ ! -f $STATE/mita-configured ]]; then
  python3 - "$STATE/settings.json" "$STATE/mita-server.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); json.dump(dict(portBindings=[dict(port=d['mieru_port'],protocol='TCP')],users=[dict(name=d['mieru_user'],password=d['mieru_password'])],loggingLevel='INFO',mtu=1400,dns=dict(dualStack='PREFER_IPv4')),open(sys.argv[2],'w'),indent=2)
PY
  mita apply config "$STATE/mita-server.json"
  mita start
  touch "$STATE/mita-configured"
fi
mita status | grep -q RUNNING || mita start

echo 'Installing nvm and Node LTS for root'
export NVM_DIR=/root/.nvm
if [[ ! -s $NVM_DIR/nvm.sh ]]; then
  install -d -m 700 "$NVM_DIR"
  backup /root/.bashrc
  download "https://raw.githubusercontent.com/nvm-sh/nvm/$NVM_TAG/install.sh" "$STATE/downloads/nvm-install.sh"
  PROFILE=/root/.bashrc METHOD=script bash "$STATE/downloads/nvm-install.sh"
fi
if ! grep -q '# vps-bootstrap nvm' /root/.bashrc; then
  backup /root/.bashrc
  cat >> /root/.bashrc <<'EOF'

# vps-bootstrap nvm
export NVM_DIR="$HOME/.nvm"
[ ! -s "$NVM_DIR/nvm.sh" ] || . "$NVM_DIR/nvm.sh"
EOF
fi
set +u
. "$NVM_DIR/nvm.sh"
if [[ ! -f $STATE/node-installed ]]; then
  nvm install --lts
  nvm alias default "$(nvm current)"
  nvm current > "$STATE/node-installed"
fi
nvm use default
set -u

echo 'Installing official Go stable release with SHA256 validation'
if [[ ! -f $STATE/go-version ]]; then
  download 'https://go.dev/dl/?mode=json' "$STATE/downloads/go-releases.json"
  python3 - "$STATE/downloads/go-releases.json" "$ARCH" > "$STATE/go-download.txt" <<'PY'
import json,sys
r=next(r for r in json.load(open(sys.argv[1])) if r['stable']); f=next(f for f in r['files'] if f['os']=='linux' and f['arch']==sys.argv[2] and f['kind']=='archive'); print(r['version']); print(f['filename']); print(f['sha256'])
PY
  mapfile -t g < "$STATE/go-download.txt"
  [[ ! -e /usr/local/go && ! -L /usr/local/go ]] || { echo 'Existing Go directory detected; refusing overwrite'; exit 1; }
  download "https://go.dev/dl/${g[1]}" "$STATE/downloads/go.tar.gz"
  printf '%s  %s\n' "${g[2]}" "$STATE/downloads/go.tar.gz" | sha256sum -c -
  install -d "/opt/vps-bootstrap/${g[0]}"
  tar -xzf "$STATE/downloads/go.tar.gz" -C "/opt/vps-bootstrap/${g[0]}"
  ln -s "/opt/vps-bootstrap/${g[0]}/go" /usr/local/go
  echo "${g[0]}" > "$STATE/go-version"
fi
if [[ ! -f /etc/profile.d/vps-bootstrap-go.sh ]]; then
  cat > /etc/profile.d/vps-bootstrap-go.sh <<'EOF'
export PATH="/usr/local/go/bin:$HOME/go/bin:$PATH"
EOF
  chmod 644 /etc/profile.d/vps-bootstrap-go.sh
fi
# .bashrc covers non-login interactive SSH shells as well.
if ! grep -q 'vps-bootstrap-go.sh' /root/.bashrc; then
  backup /root/.bashrc
  echo '. /etc/profile.d/vps-bootstrap-go.sh' >> /root/.bashrc
fi
. /etc/profile.d/vps-bootstrap-go.sh

echo 'Installing Rust stable with rustup for root'
export RUSTUP_IO_THREADS=1 RUSTUP_UNPACK_RAM=220200960 RUSTUP_CONCURRENT_DOWNLOADS=1
if [[ ! -x /root/.cargo/bin/rustup ]]; then
  backup /root/.bashrc; backup /root/.profile
  if [[ $ARCH == amd64 ]]; then RTARGET=x86_64-unknown-linux-gnu; else RTARGET=aarch64-unknown-linux-gnu; fi
  RURL="https://static.rust-lang.org/rustup/dist/$RTARGET/rustup-init"
  download "$RURL.sha256" "$STATE/downloads/rustup-init.sha256"
  RHASH=$(awk '{print $1}' "$STATE/downloads/rustup-init.sha256")
  [[ $RHASH =~ ^[a-f0-9]{64}$ ]]
  if [[ ! -f $STATE/downloads/rustup-init ]] || ! printf '%s  %s\n' "$RHASH" "$STATE/downloads/rustup-init" | sha256sum -c - >/dev/null 2>&1; then
    download "$RURL" "$STATE/downloads/rustup-init"
  fi
  printf '%s  %s\n' "$RHASH" "$STATE/downloads/rustup-init" | sha256sum -c -
  chmod 700 "$STATE/downloads/rustup-init"
  "$STATE/downloads/rustup-init" -y --profile minimal --default-toolchain stable --component rustfmt --component clippy
fi
. /root/.cargo/env
rustup set profile minimal
if ! RUSTUP_AUTO_INSTALL=0 rustup run stable rustc --version >/dev/null 2>&1 || ! rustup component list --toolchain stable --installed >/dev/null 2>&1; then
  # Remove only a broken stable toolchain before retrying; cached archives remain.
  if rustup toolchain list | grep -q '^stable-'; then rustup toolchain uninstall stable; fi
  rustup toolchain install stable --profile minimal --component rustfmt --component clippy
fi
rustup default >/dev/null 2>&1 || rustup default stable
for component in rustfmt clippy; do
  if ! rustup component list --toolchain stable --installed | grep -q "^$component-"; then
    rustup component add --toolchain stable "$component"
  fi
done

echo 'Generating private client configurations'
export STATE
python3 <<'PY'
import json,os,pathlib,subprocess,urllib.parse
p=pathlib.Path(os.environ['STATE']); d=json.load(open(p/'settings.json')); out=p/'clients'
fp=subprocess.check_output(['openssl','x509','-noout','-fingerprint','-sha256','-in','/etc/hysteria/server.crt'],text=True).strip().split('=')[1]
h=d.get('client_address',d['host']); addr=f'[{h}]' if ':' in h else h
hc=dict(server=f"{addr}:{d['hy_port']}",auth=d['hy_password'],tls=dict(sni=d['host'],insecure=True,pinSHA256=fp),obfs=dict(type='salamander',salamander=dict(password=d['hy_obfs_password'])),socks5=dict(listen='127.0.0.1:10808'))
(out/'hysteria-client.json').write_text(json.dumps(hc,indent=2)+'\n')
mc=dict(profiles=[dict(profileName='vps',user=dict(name=d['mieru_user'],password=d['mieru_password']),servers=[dict(domainName=h,portBindings=[dict(port=d['mieru_port'],protocol='TCP')])],mtu=1400)],activeProfile='vps',rpcPort=18964,socks5Port=10809,socks5ListenLAN=False,loggingLevel='INFO')
if ':' in h or h.replace('.','').isdigit():
    s=mc['profiles'][0]['servers'][0]; s['ipAddress']=s.pop('domainName')
(out/'mieru-client.json').write_text(json.dumps(mc,indent=2)+'\n')
uri=f"hysteria2://{d['hy_password']}@{addr}:{d['hy_port']}/?"+urllib.parse.urlencode(dict(sni=d['host'],insecure=1,pinSHA256=fp,obfs='salamander',**{'obfs-password':d['hy_obfs_password']}))+'#VPS-HY2'
(out/'hysteria-uri.txt').write_text(uri+'\n')
# Mihomo's documented certificate fingerprint field.
text=f'''proxies:
  - name: VPS-HY2
    type: hysteria2
    server: "{h}"
    port: {d['hy_port']}
    password: "{d['hy_password']}"
    sni: "{d['host']}"
    skip-cert-verify: true
    fingerprint: "{fp.replace(':','')}"
    obfs: salamander
    obfs-password: "{d['hy_obfs_password']}"
  - name: VPS-MIERU
    type: mieru
    server: "{h}"
    port: {d['mieru_port']}
    transport: TCP
    username: "{d['mieru_user']}"
    password: "{d['mieru_password']}"
    udp: true
'''
(out/'mihomo-proxies.yaml').write_text(text)
PY
cp /etc/hysteria/server.crt "$STATE/clients/hysteria-ca.crt"
chmod 600 "$STATE/clients/"*
# Only add rules when UFW is already active. Cloud security groups remain external.
if command -v ufw >/dev/null && ufw status | grep -q '^Status: active'; then
  ufw allow "$HY_PORT/udp"; ufw allow "$MIERU_PORT/tcp"
fi

echo 'Verifying development toolchains and proxy services'
SMOKE=$(mktemp -d "$STATE/smoke.XXXXXX")
printf 'console.log("node-ok")\n' > "$SMOKE/test.js"
node "$SMOKE/test.js"
printf 'package main\nimport "fmt"\nfunc main(){fmt.Println("go-ok")}\n' > "$SMOKE/main.go"
GOMAXPROCS=1 go build -p 1 -o "$SMOKE/go-test" "$SMOKE/main.go"
"$SMOKE/go-test"
mkdir -p "$SMOKE/rust/src"
printf '[package]\nname = "bootstrap-smoke"\nversion = "0.1.0"\nedition = "2021"\n' > "$SMOKE/rust/Cargo.toml"
printf 'fn main() {\n    println!("rust-ok");\n}\n' > "$SMOKE/rust/src/main.rs"
cargo run --offline --quiet -j 1 --manifest-path "$SMOKE/rust/Cargo.toml"
{
  date -Is
  hysteria version
  mita version
  printf 'nvm '; nvm --version
  node --version; npm --version; go version; rustc --version; cargo --version
  systemctl is-active hysteria-server mita
  systemctl is-enabled hysteria-server mita
  mita status
  free -h
  ss -lntup
  chronyc tracking
} | tee "$STATE/verification.txt"
systemctl is-active --quiet hysteria-server
systemctl is-active --quiet mita
mita status | grep -q RUNNING
if ! chronyc tracking | grep -q 'Leap status.*Normal'; then
  echo 'NTP is not synchronized yet. Check chronyc sources before using mieru.'
  exit 1
fi
echo "INSTALLATION VERIFIED. Client settings: $STATE/clients; log: $LOG"
echo "Cloud firewall requirements: UDP $HY_PORT, TCP $MIERU_PORT (IPv6 too if applicable)."
echo 'External end-to-end connectivity still requires a client-side test.'

#!/bin/bash

privkey=$(wg genkey)

printf "Enter the address for the client: "
read address

config=$(cat <<EOF

[Interface]
PrivateKey = $privkey
Address = $address/32

[Peer]
PublicKey = $(cat /etc/wireguard/public.key)
AllowedIPs = {{ wireguard.peers[hostname].address }}/32
Endpoint = {{ ansible_default_ipv4.address }}:{{ wireguard.port }}
PersistentKeepalive = 30

EOF
)

echo "$config" | qrencode -t ansiutf8

echo "Public key:"
echo "$privkey" | wg pubkey
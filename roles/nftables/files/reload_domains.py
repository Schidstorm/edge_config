#!/usr/bin/env python3

import socket
import yaml
import os

# config = {
#     "ACME_SH_IPS": [
#         "api.zerossl.com",
#         "acme.zerossl.com"
#     ],
#     "APT_IPS": [
#         "security.debian.org",
#         "help.ubuntu.com",
#         "archive.ubuntu.com",
#     ]
# }

def load_ips(domains, version):
    family = socket.AF_INET
    if version == 6:
        family = socket.AF_INET6

    ipHostnameTuple = set()
    for domain in domains:
        try:
            addrResult = socket.getaddrinfo(domain, None, family)
            for addr in addrResult:
                ipHostnameTuple.add((addr[4][0], domain))
        except socket.gaierror:
            pass

    if len(ipHostnameTuple) == 0:
        if version == 4:
            ipHostnameTuple.add(("127.0.0.1", "localhost"))
        else:
            ipHostnameTuple.add(("::1", "localhost"))
    return ipHostnameTuple

def serialize_nftables_define(name, ipHostnameTuple):
    nftables_define = f"define {name} = " + "{\n"
    ipLines = []
    first = True
    for ip, hostname in ipHostnameTuple:
        comma = ""
        if not first:
            comma = ","
        first = False

        ipLines.append(f"    {ip}{comma} # {hostname}\n")
    ipLines.reverse()
    nftables_define += "".join(ipLines)
    nftables_define += "}"


    return nftables_define

def load_config(file):
    with open(file) as f:
        return yaml.safe_load(f)
    
def serialize_nftable(config):
    nftables = []
    for key, value in config.items():
        nftables.append(serialize_nftables_define(key+"_V4", load_ips(value, 4)))
        nftables.append(serialize_nftables_define(key+"_V6", load_ips(value, 6)))
    return "\n".join(nftables)    


def check_nftables():
    return os.system("nft -f /etc/nftables.conf --check") == 0

def reload_nftables():
    if check_nftables():
        os.system("nft -f /etc/nftables.conf")

def main():
    configFile = os.getenv("CONFIG_FILE", "/etc/reload_domains.yaml")
    outputFile = os.getenv("OUTPUT_FILE", "/etc/nftables.d/reload_domains.nft")
    config = load_config(configFile)
    serialized = serialize_nftable(config)

    if os.path.exists(outputFile):
        with open(outputFile, "r") as f:
            oldSerialized = f.read()
            if oldSerialized == serialized:
                return
        
    with open(outputFile, "w") as f:
        f.truncate(0)
        f.write(serialized)

    reload_nftables()

if __name__ == "__main__":
    main()
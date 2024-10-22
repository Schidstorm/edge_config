#!/usr/bin/env python3

import socket
import yaml
import os
import typing

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
        # add localhost if no ip found because nf_tables does not allow empty sets
        if version == 4:
            ipHostnameTuple.add(("127.0.0.1", "localhost"))
        else:
            ipHostnameTuple.add(("::1", "localhost"))
    return ipHostnameTuple

def serialize_nftables_define(name, ipHostnameTuple: typing.Set[typing.Tuple[str, str]]):
    # order ipHostnameTuple by ip
    ipHostnameTuple = sorted(ipHostnameTuple, key=lambda x: x[0])

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
    

class NftablesDefines:
    ipv4: typing.Dict[str, typing.Set[typing.Tuple[str, str]]]
    ipv6: typing.Dict[str, typing.Set[typing.Tuple[str, str]]]

    def __init__(self):
        self.ipv4 = dict()
        self.ipv6 = dict()

    def add_domains(self, key, domains: typing.Set[str]):
        self.ipv4[key] = load_ips(domains, 4)
        self.ipv6[key] = load_ips(domains, 6)

    def __eq__(self, value):
        return self.ipv4 == value.ipv4 and self.ipv6 == value.ipv6
    
    def __ne__(self, value):
        return not self.__eq__(value)
    
    def serialize(self):
        keys = set(self.ipv4.keys()).union(set(self.ipv6.keys()))
        # sort keys
        keys = sorted(keys)

        defines = []
        for key in keys:
            if key not in self.ipv4:
                continue
            value = self.ipv4[key]

            defines.append(serialize_nftables_define(key+"_V4", value))

        for key in keys:
            if key not in self.ipv6:
                continue
            value = self.ipv6[key]

            defines.append(serialize_nftables_define(key+"_V6", value))

        return "\n".join(defines)   

def load_defines(config):
    defines = NftablesDefines()
    for key, value in config.items():
        defines.add_domains(key, value)
    return defines

def check_nftables():
    return os.system("nft -f /etc/nftables.conf --check") == 0

def reload_nftables():
    if check_nftables():
        os.system("nft -f /etc/nftables.conf")

def main():
    configFile = os.getenv("CONFIG_FILE", "/etc/reload_domains.yaml")
    outputFile = os.getenv("OUTPUT_FILE", "/etc/nftables.d/reload_domains.nft")
    config = load_config(configFile)
    defines = load_defines(config)
    serialized = defines.serialize()

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
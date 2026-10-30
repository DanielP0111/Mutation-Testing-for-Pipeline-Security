#!/usr/bin/env bash

set -eu

declare xz_url="https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/xz-utils/5.6.0-0.2/xz-utils_5.6.0.orig.tar.xz"
declare xz_tarfile="xz-utils_5.6.0.orig.tar.xz" 

rm -fr demo/xz-5.6.0/
mkdir -p demo
>/dev/null pushd demo

if [[ ! -f "$xz_tarfile" ]]; then wget "$xz_url"; fi

tar xvf "$xz_tarfile"
export RPM_ARCH=x86_64

cat <<EOF >xz-5.6.0/build_phases.json
[
    {
        "name": "autogen",
        "commands": [["./autogen.sh"]]
    },
    {
        "name": "configure",
        "commands": [["./configure"]]
    },
    {
        "name": "make",
        "commands": [["make", "-j", "8"]],
        "permissions": {
            "file": {
                "restricted": ["tests/files/"]
            }
        }
    }
]
EOF

python3.14 ../foreman.py -C xz-5.6.0/
cat xz-5.6.0/warnings*

>/dev/null popd

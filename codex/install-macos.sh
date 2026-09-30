#!/bin/sh
set -eu
package_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 "$package_dir/install.py" --project "$package_dir/../my-seed-ir" --team 'My Team' --with-deps

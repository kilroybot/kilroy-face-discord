#!/bin/bash --login

set +euo pipefail
conda activate kilroy-face-discord
set -euo pipefail

exec "$@"

#!/usr/bin/env bash
set -euo pipefail

"$(dirname "$0")/setup_tools.sh"
"$(dirname "$0")/run_openram.sh"
"$(dirname "$0")/run_sim.sh"
"$(dirname "$0")/run_spike_example.sh"
"$(dirname "$0")/run_synth.sh"
"$(dirname "$0")/run_sta.sh"

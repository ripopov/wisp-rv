SHELL := /usr/bin/env bash

.PHONY: setup openram sim spike synth sta flow clean

setup:
	bash ./scripts/setup_tools.sh

openram:
	bash ./scripts/run_openram.sh

sim:
	bash ./scripts/run_sim.sh

spike:
	bash ./scripts/run_spike_example.sh

synth:
	bash ./scripts/run_synth.sh

sta:
	bash ./scripts/run_sta.sh

flow: setup openram sim spike synth sta

clean:
	rm -rf ./build ./reports/sta

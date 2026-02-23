SHELL := /usr/bin/env bash

.PHONY: setup openram sim synth sta flow clean

setup:
	bash ./scripts/setup_tools.sh

openram:
	bash ./scripts/run_openram.sh

sim:
	bash ./scripts/run_sim.sh

synth:
	bash ./scripts/run_synth.sh

sta:
	bash ./scripts/run_sta.sh

flow: setup openram sim synth sta

clean:
	rm -rf ./build ./reports/sta

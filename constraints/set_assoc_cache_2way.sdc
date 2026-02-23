create_clock -name clk -period 4.000 [get_ports clk]
set_clock_uncertainty 0.050 [get_clocks clk]

set non_clock_inputs [get_ports {rst_n req_valid req_write req_addr[*] req_wdata[*] req_wmask[*]}]
set_input_delay 0.200 -clock clk $non_clock_inputs
set_input_transition 0.050 $non_clock_inputs
set_false_path -from [get_ports rst_n]

set_output_delay 0.200 -clock clk [all_outputs]
set_load 0.050 [all_outputs]

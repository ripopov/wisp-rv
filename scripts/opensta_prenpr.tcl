read_liberty $::env(NANGATE45_LIB)
read_liberty $::env(OPENRAM_DATA_LIB)
read_liberty $::env(OPENRAM_TAG_LIB)

read_verilog $::env(SYNTH_NETLIST)
link_design set_assoc_cache_2way

read_sdc $::env(SDC_FILE)

report_checks -path_delay max -digits 3 -group_path_count 20 > $::env(STA_OUT)/checks_max.rpt
report_checks -path_delay min -digits 3 -group_path_count 20 > $::env(STA_OUT)/checks_min.rpt
report_worst_slack -max > $::env(STA_OUT)/wns_max.rpt
report_worst_slack -min > $::env(STA_OUT)/wns_min.rpt
report_tns > $::env(STA_OUT)/tns.rpt

exit

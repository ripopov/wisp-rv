if {![info exists ::env(NANGATE45_LIB)]} {
    puts stderr "Missing required env var: NANGATE45_LIB"
    exit 1
}
if {![info exists ::env(STUDY_NETLIST)]} {
    puts stderr "Missing required env var: STUDY_NETLIST"
    exit 1
}
if {![info exists ::env(STUDY_TOP)]} {
    puts stderr "Missing required env var: STUDY_TOP"
    exit 1
}
if {![info exists ::env(STUDY_SDC)]} {
    puts stderr "Missing required env var: STUDY_SDC"
    exit 1
}
if {![info exists ::env(STA_OUT)]} {
    puts stderr "Missing required env var: STA_OUT"
    exit 1
}

read_liberty $::env(NANGATE45_LIB)

if {[info exists ::env(STUDY_EXTRA_LIBS)]} {
    set extra_libs [string trim $::env(STUDY_EXTRA_LIBS)]
    if {[string length $extra_libs] > 0} {
        foreach lib_path [split $extra_libs " "] {
            if {[string length $lib_path] > 0} {
                read_liberty $lib_path
            }
        }
    }
}

read_verilog $::env(STUDY_NETLIST)
link_design $::env(STUDY_TOP)
read_sdc $::env(STUDY_SDC)

report_checks -path_delay max -digits 3 -group_path_count 20 > $::env(STA_OUT)/checks_max.rpt
report_checks -path_delay min -digits 3 -group_path_count 20 > $::env(STA_OUT)/checks_min.rpt
report_worst_slack -max > $::env(STA_OUT)/wns_max.rpt
report_worst_slack -min > $::env(STA_OUT)/wns_min.rpt
report_tns > $::env(STA_OUT)/tns.rpt

exit

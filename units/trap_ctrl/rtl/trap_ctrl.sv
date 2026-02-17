/*
 * Module: trap_ctrl
 * Purpose: Generate trap/mret redirects and corresponding mstatus update values.
 * Interface: Trap and mret requests plus CSR state in; redirect and CSR-update intents out.
 * Behavior: Pure combinational control with trap entry priority over mret.
 * Reset: Not applicable (combinational module).
 * Pipeline control: Emits redirect targets for trap entry and mret return.
 * Corner cases: mret restores MIE from MPIE and forces MPIE=1.
 */
module trap_ctrl (
    input  logic        trap_enter_valid,
    input  logic [63:0] trap_cause,
    input  logic [63:0] trap_tval,
    input  logic [63:0] trap_pc,
    input  logic        mret_valid,

    input  logic [63:0] csr_mstatus,
    input  logic [63:0] csr_mtvec,
    input  logic [63:0] csr_mepc,

    output logic        redirect_valid,
    output logic [63:0] redirect_pc,

    output logic        trap_update_valid,
    output logic [63:0] trap_mepc,
    output logic [63:0] trap_mcause,
    output logic [63:0] trap_mtval,
    output logic [63:0] trap_mstatus_new,

    output logic        mret_update_valid,
    output logic [63:0] mret_mstatus_new
);
    import rv64_pkg::*;

    logic old_mie;
    logic old_mpie;

    assign old_mie = csr_mstatus[3];
    assign old_mpie = csr_mstatus[7];

    always_comb begin
        redirect_valid = 1'b0;
        redirect_pc = 64'd0;

        trap_update_valid = 1'b0;
        trap_mepc = 64'd0;
        trap_mcause = 64'd0;
        trap_mtval = 64'd0;
        trap_mstatus_new = csr_mstatus & MSTATUS_STAGE08_MASK;

        mret_update_valid = 1'b0;
        mret_mstatus_new = csr_mstatus & MSTATUS_STAGE08_MASK;

        if (trap_enter_valid) begin
            redirect_valid = 1'b1;
            redirect_pc = {csr_mtvec[63:2], 2'b00};

            trap_update_valid = 1'b1;
            trap_mepc = {trap_pc[63:2], 2'b00};
            trap_mcause = trap_cause;
            trap_mtval = trap_tval;

            trap_mstatus_new = csr_mstatus & MSTATUS_STAGE08_MASK;
            trap_mstatus_new[7] = old_mie;
            trap_mstatus_new[3] = 1'b0;
            trap_mstatus_new[12:11] = 2'b11;
        end else if (mret_valid) begin
            redirect_valid = 1'b1;
            redirect_pc = {csr_mepc[63:2], 2'b00};

            mret_update_valid = 1'b1;
            mret_mstatus_new = csr_mstatus & MSTATUS_STAGE08_MASK;
            mret_mstatus_new[3] = old_mpie;
            mret_mstatus_new[7] = 1'b1;
            mret_mstatus_new[12:11] = 2'b00;
        end
    end
endmodule

/*
 * Module: commit_ctrl
 * Purpose: Decide retirement, CSR commit, and precise trap entry from WB-stage metadata.
 * Interface: WB metadata and CSR-access status in; commit/trap/mret control intents out.
 * Behavior: Pure combinational priority logic with trap suppression of writeback/retire.
 * Reset: Not applicable (combinational module).
 * Pipeline control: Produces redirect-trigger inputs consumed by trap_ctrl.
 * Corner cases: Illegal CSR access is treated as illegal-instruction trap.
 */
module commit_ctrl (
    input  logic        wb_valid,
    input  logic [63:0] wb_pc,
    input  logic [31:0] wb_instr,
    input  logic        wb_reg_write,

    input  logic        wb_is_csr,
    input  logic [2:0]  wb_csr_cmd,
    input  logic [11:0] wb_csr_addr,
    input  logic [63:0] wb_csr_wdata,

    input  logic        wb_trap_illegal,
    input  logic        wb_trap_ecall,
    input  logic        wb_trap_ebreak,
    input  logic        wb_is_mret,

    input  logic        csr_access_illegal,

    output logic        wb_allow_reg_write,
    output logic        retire_valid,

    output logic        csr_commit_valid,
    output logic [2:0]  csr_commit_cmd,
    output logic [11:0] csr_commit_addr,
    output logic [63:0] csr_commit_wdata,

    output logic        trap_enter_valid,
    output logic [63:0] trap_cause,
    output logic [63:0] trap_tval,
    output logic [63:0] trap_pc,

    output logic        mret_valid
);
    import rv64_pkg::*;

    logic trap_illegal_effective;

    always_comb begin
        trap_illegal_effective = wb_trap_illegal || (wb_is_csr && csr_access_illegal);

        trap_enter_valid = 1'b0;
        trap_cause = 64'd0;
        trap_tval = 64'd0;
        trap_pc = wb_pc;

        if (wb_valid) begin
            if (trap_illegal_effective) begin
                trap_enter_valid = 1'b1;
                trap_cause = MCAUSE_ILLEGAL_INSTR;
                trap_tval = {32'd0, wb_instr};
            end else if (wb_trap_ebreak) begin
                trap_enter_valid = 1'b1;
                trap_cause = MCAUSE_BREAKPOINT;
                trap_tval = 64'd0;
            end else if (wb_trap_ecall) begin
                trap_enter_valid = 1'b1;
                trap_cause = MCAUSE_ECALL_MMODE;
                trap_tval = 64'd0;
            end
        end

        mret_valid = wb_valid && wb_is_mret && !trap_enter_valid;
        retire_valid = wb_valid && !trap_enter_valid;
        wb_allow_reg_write = wb_valid && wb_reg_write && !trap_enter_valid;

        csr_commit_valid = wb_valid && wb_is_csr && !trap_enter_valid;
        csr_commit_cmd = wb_csr_cmd;
        csr_commit_addr = wb_csr_addr;
        csr_commit_wdata = wb_csr_wdata;
    end
endmodule

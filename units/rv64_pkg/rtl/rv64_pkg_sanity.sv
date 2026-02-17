/*
 * Module: rv64_pkg_sanity
 * Purpose: Expose rv64_pkg constants/enums for cocotb validation.
 * Interface: Constant-value outputs for opcode and enum sanity checks.
 * Behavior: Pure combinational constant wiring.
 * Reset: Not applicable.
 * Pipeline control: Not applicable.
 * Corner cases: Ensures ALU op and format encodings stay stable across refactors.
 */
module rv64_pkg_sanity (
    output logic [6:0] opcode_op,
    output logic [6:0] opcode_op_imm,
    output logic [6:0] opcode_op_32,
    output logic [6:0] opcode_op_imm_32,
    output logic [6:0] opcode_load,
    output logic [6:0] opcode_store,
    output logic [3:0] alu_add,
    output logic [3:0] alu_sra,
    output logic [2:0] fmt_i,
    output logic [2:0] fmt_j
);
    import rv64_pkg::*;

    assign opcode_op = OP;
    assign opcode_op_imm = OP_IMM;
    assign opcode_op_32 = OP_32;
    assign opcode_op_imm_32 = OP_IMM_32;
    assign opcode_load = LOAD;
    assign opcode_store = STORE;
    assign alu_add = ALU_OP_ADD;
    assign alu_sra = ALU_OP_SRA;
    assign fmt_i = I_TYPE;
    assign fmt_j = J_TYPE;
endmodule

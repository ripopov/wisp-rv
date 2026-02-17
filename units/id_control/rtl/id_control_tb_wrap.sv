/*
 * Module: id_control_tb_wrap
 * Purpose: Flatten id_control packed struct outputs for cocotb visibility.
 * Interface: opcode/funct fields in, individual control bits and ALU op out.
 * Behavior: Pure combinational wrapper around id_control.
 * Reset: Not applicable.
 * Pipeline control: Mirrors downstream control signals from decode.
 * Corner cases: Preserves enum encodings by direct field assignment.
 */
module id_control_tb_wrap (
    input  logic [6:0] opcode,
    input  logic [2:0] funct3,
    input  logic [6:0] funct7,
    output logic [3:0] alu_op,
    output logic       alu_src,
    output logic       mem_read,
    output logic       mem_write,
    output logic       reg_write,
    output logic       mem_to_reg,
    output logic       branch,
    output logic       jump,
    output logic       is_word_op
);
    import rv64_pkg::*;

    id_ctrl_t ctrl;

    id_control u_id_control (
        .opcode(opcode),
        .funct3(funct3),
        .funct7(funct7),
        .ctrl(ctrl)
    );

    assign alu_op = ctrl.alu_op;
    assign alu_src = ctrl.alu_src;
    assign mem_read = ctrl.mem_read;
    assign mem_write = ctrl.mem_write;
    assign reg_write = ctrl.reg_write;
    assign mem_to_reg = ctrl.mem_to_reg;
    assign branch = ctrl.branch;
    assign jump = ctrl.jump;
    assign is_word_op = ctrl.is_word_op;
endmodule

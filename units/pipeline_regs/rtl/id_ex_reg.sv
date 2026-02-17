/*
 * Module: id_ex_reg
 * Purpose: Pipeline register between ID and EX stages.
 * Interface: Stall/flush controls plus decoded ID payload and control signals.
 * Behavior: Captures ID payload on rising edge unless stalled.
 * Reset: Active-high synchronous reset clears register contents and valid.
 * Pipeline control: Flush has priority over stall and inserts an invalid bubble.
 * Corner cases: Flush+stall in same cycle clears the register.
 */
module id_ex_reg (
    input  logic        clk,
    input  logic        rst,
    input  logic        stall,
    input  logic        flush,
    input  logic [63:0] pc_in,
    input  logic [31:0] instr_in,
    input  logic [63:0] rs1_data_in,
    input  logic [63:0] rs2_data_in,
    input  logic [63:0] imm_in,
    input  logic [6:0]  opcode_in,
    input  logic [4:0]  rd_in,
    input  logic [4:0]  rs1_addr_in,
    input  logic [4:0]  rs2_addr_in,
    input  logic [2:0]  funct3_in,
    input  logic [6:0]  funct7_in,
    input  logic        is_csr_in,
    input  logic [2:0]  csr_cmd_in,
    input  logic [11:0] csr_addr_in,
    input  logic [4:0]  csr_zimm_in,
    input  logic        csr_use_imm_in,
    input  logic        trap_illegal_in,
    input  logic        trap_ecall_in,
    input  logic        trap_ebreak_in,
    input  logic        is_mret_in,
    input  logic [3:0]  alu_op_in,
    input  logic        alu_src_in,
    input  logic        mem_read_in,
    input  logic        mem_write_in,
    input  logic        reg_write_in,
    input  logic        mem_to_reg_in,
    input  logic        branch_in,
    input  logic        jump_in,
    input  logic        is_word_op_in,
    input  logic        valid_in,
    output logic [63:0] pc_out,
    output logic [31:0] instr_out,
    output logic [63:0] rs1_data_out,
    output logic [63:0] rs2_data_out,
    output logic [63:0] imm_out,
    output logic [6:0]  opcode_out,
    output logic [4:0]  rd_out,
    output logic [4:0]  rs1_addr_out,
    output logic [4:0]  rs2_addr_out,
    output logic [2:0]  funct3_out,
    output logic [6:0]  funct7_out,
    output logic        is_csr_out,
    output logic [2:0]  csr_cmd_out,
    output logic [11:0] csr_addr_out,
    output logic [4:0]  csr_zimm_out,
    output logic        csr_use_imm_out,
    output logic        trap_illegal_out,
    output logic        trap_ecall_out,
    output logic        trap_ebreak_out,
    output logic        is_mret_out,
    output logic [3:0]  alu_op_out,
    output logic        alu_src_out,
    output logic        mem_read_out,
    output logic        mem_write_out,
    output logic        reg_write_out,
    output logic        mem_to_reg_out,
    output logic        branch_out,
    output logic        jump_out,
    output logic        is_word_op_out,
    output logic        valid_out
);
    import rv64_pkg::*;

    id_ex_reg_t in_data;
    id_ex_reg_t reg_q;

    always_comb begin
        in_data = '0;
        in_data.pc = pc_in;
        in_data.instr = instr_in;
        in_data.rs1_data = rs1_data_in;
        in_data.rs2_data = rs2_data_in;
        in_data.imm = imm_in;
        in_data.opcode = opcode_in;
        in_data.rd = rd_in;
        in_data.rs1_addr = rs1_addr_in;
        in_data.rs2_addr = rs2_addr_in;
        in_data.funct3 = funct3_in;
        in_data.funct7 = funct7_in;
        in_data.is_csr = is_csr_in;
        in_data.csr_cmd = csr_cmd_t'(csr_cmd_in);
        in_data.csr_addr = csr_addr_in;
        in_data.csr_zimm = csr_zimm_in;
        in_data.csr_use_imm = csr_use_imm_in;
        in_data.trap_illegal = trap_illegal_in;
        in_data.trap_ecall = trap_ecall_in;
        in_data.trap_ebreak = trap_ebreak_in;
        in_data.is_mret = is_mret_in;
        in_data.ctrl.alu_op = alu_op_t'(alu_op_in);
        in_data.ctrl.alu_src = alu_src_t'(alu_src_in);
        in_data.ctrl.mem_read = mem_read_in;
        in_data.ctrl.mem_write = mem_write_in;
        in_data.ctrl.reg_write = reg_write_in;
        in_data.ctrl.mem_to_reg = mem_to_reg_in;
        in_data.ctrl.branch = branch_in;
        in_data.ctrl.jump = jump_in;
        in_data.ctrl.is_word_op = is_word_op_in;
        in_data.valid = valid_in;
    end

    always_ff @(posedge clk) begin
        if (rst || flush) begin
            reg_q <= '0;
        end else if (!stall) begin
            reg_q <= in_data;
        end
    end

    assign pc_out = reg_q.pc;
    assign instr_out = reg_q.instr;
    assign rs1_data_out = reg_q.rs1_data;
    assign rs2_data_out = reg_q.rs2_data;
    assign imm_out = reg_q.imm;
    assign opcode_out = reg_q.opcode;
    assign rd_out = reg_q.rd;
    assign rs1_addr_out = reg_q.rs1_addr;
    assign rs2_addr_out = reg_q.rs2_addr;
    assign funct3_out = reg_q.funct3;
    assign funct7_out = reg_q.funct7;
    assign is_csr_out = reg_q.is_csr;
    assign csr_cmd_out = reg_q.csr_cmd;
    assign csr_addr_out = reg_q.csr_addr;
    assign csr_zimm_out = reg_q.csr_zimm;
    assign csr_use_imm_out = reg_q.csr_use_imm;
    assign trap_illegal_out = reg_q.trap_illegal;
    assign trap_ecall_out = reg_q.trap_ecall;
    assign trap_ebreak_out = reg_q.trap_ebreak;
    assign is_mret_out = reg_q.is_mret;
    assign alu_op_out = reg_q.ctrl.alu_op;
    assign alu_src_out = reg_q.ctrl.alu_src;
    assign mem_read_out = reg_q.ctrl.mem_read;
    assign mem_write_out = reg_q.ctrl.mem_write;
    assign reg_write_out = reg_q.ctrl.reg_write;
    assign mem_to_reg_out = reg_q.ctrl.mem_to_reg;
    assign branch_out = reg_q.ctrl.branch;
    assign jump_out = reg_q.ctrl.jump;
    assign is_word_op_out = reg_q.ctrl.is_word_op;
    assign valid_out = reg_q.valid;
endmodule

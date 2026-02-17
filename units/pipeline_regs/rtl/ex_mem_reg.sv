/*
 * Module: ex_mem_reg
 * Purpose: Pipeline register between EX and MEM stages.
 * Interface: Stall/flush controls plus EX payload and memory/writeback control signals.
 * Behavior: Captures EX payload on rising edge unless stalled.
 * Reset: Active-high synchronous reset clears register contents and valid.
 * Pipeline control: Flush has priority over stall and inserts an invalid bubble.
 * Corner cases: Flush+stall in same cycle clears valid and payload state.
 */
module ex_mem_reg (
    input  logic        clk,
    input  logic        rst,
    input  logic        stall,
    input  logic        flush,
    input  logic [63:0] pc_in,
    input  logic [31:0] instr_in,
    input  logic [63:0] alu_result_in,
    input  logic [63:0] rs2_data_in,
    input  logic [63:0] csr_wdata_in,
    input  logic [4:0]  rd_in,
    input  logic [2:0]  funct3_in,
    input  logic        is_csr_in,
    input  logic [2:0]  csr_cmd_in,
    input  logic [11:0] csr_addr_in,
    input  logic        trap_illegal_in,
    input  logic        trap_ecall_in,
    input  logic        trap_ebreak_in,
    input  logic        is_mret_in,
    input  logic        mem_read_in,
    input  logic        mem_write_in,
    input  logic        reg_write_in,
    input  logic        mem_to_reg_in,
    input  logic        is_word_op_in,
    input  logic        branch_taken_in,
    input  logic [63:0] branch_target_in,
    input  logic        valid_in,
    output logic [63:0] pc_out,
    output logic [31:0] instr_out,
    output logic [63:0] alu_result_out,
    output logic [63:0] rs2_data_out,
    output logic [63:0] csr_wdata_out,
    output logic [4:0]  rd_out,
    output logic [2:0]  funct3_out,
    output logic        is_csr_out,
    output logic [2:0]  csr_cmd_out,
    output logic [11:0] csr_addr_out,
    output logic        trap_illegal_out,
    output logic        trap_ecall_out,
    output logic        trap_ebreak_out,
    output logic        is_mret_out,
    output logic        mem_read_out,
    output logic        mem_write_out,
    output logic        reg_write_out,
    output logic        mem_to_reg_out,
    output logic        is_word_op_out,
    output logic        branch_taken_out,
    output logic [63:0] branch_target_out,
    output logic        valid_out
);
    import rv64_pkg::*;

    ex_mem_reg_t in_data;
    ex_mem_reg_t reg_q;

    always_comb begin
        in_data = '0;
        in_data.pc = pc_in;
        in_data.instr = instr_in;
        in_data.alu_result = alu_result_in;
        in_data.rs2_data = rs2_data_in;
        in_data.csr_wdata = csr_wdata_in;
        in_data.rd = rd_in;
        in_data.funct3 = funct3_in;
        in_data.is_csr = is_csr_in;
        in_data.csr_cmd = csr_cmd_t'(csr_cmd_in);
        in_data.csr_addr = csr_addr_in;
        in_data.trap_illegal = trap_illegal_in;
        in_data.trap_ecall = trap_ecall_in;
        in_data.trap_ebreak = trap_ebreak_in;
        in_data.is_mret = is_mret_in;
        in_data.ctrl.mem_read = mem_read_in;
        in_data.ctrl.mem_write = mem_write_in;
        in_data.ctrl.reg_write = reg_write_in;
        in_data.ctrl.mem_to_reg = mem_to_reg_in;
        in_data.ctrl.is_word_op = is_word_op_in;
        in_data.branch_taken = branch_taken_in;
        in_data.branch_target = branch_target_in;
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
    assign alu_result_out = reg_q.alu_result;
    assign rs2_data_out = reg_q.rs2_data;
    assign csr_wdata_out = reg_q.csr_wdata;
    assign rd_out = reg_q.rd;
    assign funct3_out = reg_q.funct3;
    assign is_csr_out = reg_q.is_csr;
    assign csr_cmd_out = reg_q.csr_cmd;
    assign csr_addr_out = reg_q.csr_addr;
    assign trap_illegal_out = reg_q.trap_illegal;
    assign trap_ecall_out = reg_q.trap_ecall;
    assign trap_ebreak_out = reg_q.trap_ebreak;
    assign is_mret_out = reg_q.is_mret;
    assign mem_read_out = reg_q.ctrl.mem_read;
    assign mem_write_out = reg_q.ctrl.mem_write;
    assign reg_write_out = reg_q.ctrl.reg_write;
    assign mem_to_reg_out = reg_q.ctrl.mem_to_reg;
    assign is_word_op_out = reg_q.ctrl.is_word_op;
    assign branch_taken_out = reg_q.branch_taken;
    assign branch_target_out = reg_q.branch_target;
    assign valid_out = reg_q.valid;
endmodule

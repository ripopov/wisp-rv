/*
 * Module: mem_wb_reg
 * Purpose: Pipeline register between MEM and WB stages.
 * Interface: Stall/flush controls plus MEM payload and writeback control signals.
 * Behavior: Captures MEM payload on rising edge unless stalled.
 * Reset: Active-high synchronous reset clears register contents and valid.
 * Pipeline control: Flush has priority over stall and inserts an invalid bubble.
 * Corner cases: Flush+stall in same cycle clears valid and control bits.
 */
module mem_wb_reg (
    input  logic        clk,
    input  logic        rst,
    input  logic        stall,
    input  logic        flush,
    input  logic [63:0] alu_result_in,
    input  logic [63:0] mem_data_in,
    input  logic [4:0]  rd_in,
    input  logic        reg_write_in,
    input  logic        mem_to_reg_in,
    input  logic        valid_in,
    output logic [63:0] alu_result_out,
    output logic [63:0] mem_data_out,
    output logic [4:0]  rd_out,
    output logic        reg_write_out,
    output logic        mem_to_reg_out,
    output logic        valid_out
);
    import rv64_pkg::*;

    mem_wb_reg_t in_data;
    mem_wb_reg_t reg_q;

    always_comb begin
        in_data = '0;
        in_data.alu_result = alu_result_in;
        in_data.mem_data = mem_data_in;
        in_data.rd = rd_in;
        in_data.ctrl.reg_write = reg_write_in;
        in_data.ctrl.mem_to_reg = mem_to_reg_in;
        in_data.valid = valid_in;
    end

    always_ff @(posedge clk) begin
        if (rst || flush) begin
            reg_q <= '0;
        end else if (!stall) begin
            reg_q <= in_data;
        end
    end

    assign alu_result_out = reg_q.alu_result;
    assign mem_data_out = reg_q.mem_data;
    assign rd_out = reg_q.rd;
    assign reg_write_out = reg_q.ctrl.reg_write;
    assign mem_to_reg_out = reg_q.ctrl.mem_to_reg;
    assign valid_out = reg_q.valid;
endmodule

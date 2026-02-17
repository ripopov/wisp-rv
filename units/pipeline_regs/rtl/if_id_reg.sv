/*
 * Module: if_id_reg
 * Purpose: Pipeline register between IF and ID stages.
 * Interface: Stall/flush controls plus IF payload (pc, instr, valid).
 * Behavior: Captures new payload on each rising edge unless stalled.
 * Reset: Active-high synchronous reset clears the register to a bubble.
 * Pipeline control: Flush has priority over stall and inserts an invalid bubble.
 * Corner cases: Stall holds all fields stable; flush+stall still clears valid.
 */
module if_id_reg (
    input  logic        clk,
    input  logic        rst,
    input  logic        stall,
    input  logic        flush,
    input  logic [63:0] pc_in,
    input  logic [31:0] instr_in,
    input  logic        valid_in,
    output logic [63:0] pc_out,
    output logic [31:0] instr_out,
    output logic        valid_out
);
    import rv64_pkg::*;

    if_id_reg_t in_data;
    if_id_reg_t reg_q;

    always_comb begin
        in_data = '0;
        in_data.pc = pc_in;
        in_data.instr = instr_in;
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
    assign valid_out = reg_q.valid;
endmodule

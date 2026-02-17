/*
 * Module: regfile
 * Purpose: RV64 integer register file with two read ports and one write port.
 * Interface: clk/rst, rs1/rs2 read addresses, write enable/address/data, read data outputs.
 * Behavior: Synchronous writes on clk edge; combinational reads with same-cycle write bypass.
 * Reset: Active-high synchronous reset clears all architectural registers to zero.
 * Pipeline control: x0 is hardwired to zero and bypass does not override x0 behavior.
 * Corner cases: If read and write target the same non-zero register in one cycle, read returns wr_data.
 */
module regfile (
    input  logic        clk,
    input  logic        rst,
    input  logic [4:0]  rs1_addr,
    input  logic [4:0]  rs2_addr,
    input  logic        wr_en,
    input  logic [4:0]  wr_addr,
    input  logic [63:0] wr_data,
    output logic [63:0] rs1_data,
    output logic [63:0] rs2_data
);
    logic [63:0] regs [31:0];
    integer idx;

    always_ff @(posedge clk) begin
        if (rst) begin
            for (idx = 0; idx < 32; idx = idx + 1) begin
                regs[idx] <= 64'd0;
            end
        end else if (wr_en && (wr_addr != 5'd0)) begin
            regs[wr_addr] <= wr_data;
        end
    end

    always_comb begin
        if (rs1_addr == 5'd0) begin
            rs1_data = 64'd0;
        end else if (wr_en && !rst && (wr_addr == rs1_addr) && (wr_addr != 5'd0)) begin
            rs1_data = wr_data;
        end else begin
            rs1_data = regs[rs1_addr];
        end

        if (rs2_addr == 5'd0) begin
            rs2_data = 64'd0;
        end else if (wr_en && !rst && (wr_addr == rs2_addr) && (wr_addr != 5'd0)) begin
            rs2_data = wr_data;
        end else begin
            rs2_data = regs[rs2_addr];
        end
    end
endmodule

/*
 * Module: forwarding_unit
 * Purpose: Select EX operand bypass sources from EX/MEM and MEM/WB stages.
 * Interface: Prior-stage writeback metadata plus current EX source register IDs in, forward-select controls out.
 * Behavior: Pure combinational compare network with EX/MEM priority over MEM/WB.
 * Reset: Not applicable (combinational module).
 * Pipeline control: Produces independent forwarding decisions for rs1 and rs2 each cycle.
 * Corner cases: Never forwards writes targeting x0.
 */
module forwarding_unit (
    input  logic       ex_mem_reg_write,
    input  logic [4:0] ex_mem_rd,
    input  logic       mem_wb_reg_write,
    input  logic [4:0] mem_wb_rd,
    input  logic [4:0] id_ex_rs1,
    input  logic [4:0] id_ex_rs2,
    output logic [1:0] forward_a_sel,
    output logic [1:0] forward_b_sel
);
    localparam logic [1:0] FWD_NONE   = 2'b00;
    localparam logic [1:0] FWD_EX_MEM = 2'b01;
    localparam logic [1:0] FWD_MEM_WB = 2'b10;

    always_comb begin
        forward_a_sel = FWD_NONE;
        forward_b_sel = FWD_NONE;

        if (ex_mem_reg_write && (ex_mem_rd != 5'd0) && (ex_mem_rd == id_ex_rs1)) begin
            forward_a_sel = FWD_EX_MEM;
        end else if (mem_wb_reg_write && (mem_wb_rd != 5'd0) && (mem_wb_rd == id_ex_rs1)) begin
            forward_a_sel = FWD_MEM_WB;
        end

        if (ex_mem_reg_write && (ex_mem_rd != 5'd0) && (ex_mem_rd == id_ex_rs2)) begin
            forward_b_sel = FWD_EX_MEM;
        end else if (mem_wb_reg_write && (mem_wb_rd != 5'd0) && (mem_wb_rd == id_ex_rs2)) begin
            forward_b_sel = FWD_MEM_WB;
        end
    end
endmodule

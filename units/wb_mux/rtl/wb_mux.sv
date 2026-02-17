/*
 * Module: wb_mux
 * Purpose: Select the register writeback value in WB stage.
 * Interface: ALU result, memory load data, PC+4 link value, and 2-bit source select.
 * Behavior: Pure combinational 3-way source mux.
 * Reset: Not applicable (combinational module).
 * Pipeline control: Source select is expected to come from WB control logic.
 * Corner cases: Default falls back to ALU result for unsupported select values.
 */
module wb_mux (
    input  logic [63:0] alu_result,
    input  logic [63:0] mem_data,
    input  logic [63:0] pc_plus4,
    input  logic [1:0]  wb_sel,
    output logic [63:0] wb_data
);
    always_comb begin
        unique case (wb_sel)
            2'b00: wb_data = alu_result;
            2'b01: wb_data = mem_data;
            2'b10: wb_data = pc_plus4;
            default: wb_data = alu_result;
        endcase
    end
endmodule

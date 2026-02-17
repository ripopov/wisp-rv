/*
 * Module: pc_select
 * Purpose: Select the next program counter for the IF stage.
 * Interface: Current PC, stall, redirect-valid, redirect target, and selected next PC.
 * Behavior: Combinational priority mux with redirect over stall over sequential increment.
 * Reset: Not applicable (combinational module).
 * Pipeline control: Redirect overrides stall so control-flow changes are never blocked.
 * Corner cases: Sequential path increments by 4 bytes (RV64 base instruction size).
 */
module pc_select (
    input  logic [63:0] current_pc,
    input  logic        stall,
    input  logic        redirect_valid,
    input  logic [63:0] redirect_pc,
    output logic [63:0] next_pc
);
    always_comb begin
        if (redirect_valid) begin
            next_pc = redirect_pc;
        end else if (stall) begin
            next_pc = current_pc;
        end else begin
            next_pc = current_pc + 64'd4;
        end
    end
endmodule

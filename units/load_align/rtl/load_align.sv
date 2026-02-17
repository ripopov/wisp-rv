/*
 * Module: load_align
 * Purpose: Extract and sign/zero-extend RV64 load data from a 64-bit memory word.
 * Interface: Raw memory read data, byte offset, funct3 width selector, aligned 64-bit load data.
 * Behavior: Pure combinational byte-lane extraction with width-specific extension.
 * Reset: Not applicable (combinational module).
 * Pipeline control: Not applicable.
 * Corner cases: LW sign-extends while LWU zero-extends; byte offset shifts extraction window.
 */
module load_align (
    input  logic [63:0] mem_rdata,
    input  logic [2:0]  addr_lsb,
    input  logic [2:0]  funct3,
    output logic [63:0] load_data
);
    import rv64_pkg::*;

    logic [5:0]  shift_amt;
    logic [63:0] shifted_data;

    assign shift_amt = {addr_lsb, 3'b000};
    assign shifted_data = mem_rdata >> shift_amt;

    always_comb begin
        unique case (funct3)
            F3_LB:  load_data = {{56{shifted_data[7]}}, shifted_data[7:0]};
            F3_LH:  load_data = {{48{shifted_data[15]}}, shifted_data[15:0]};
            F3_LW:  load_data = {{32{shifted_data[31]}}, shifted_data[31:0]};
            F3_LD:  load_data = shifted_data;
            F3_LBU: load_data = {56'd0, shifted_data[7:0]};
            F3_LHU: load_data = {48'd0, shifted_data[15:0]};
            F3_LWU: load_data = {32'd0, shifted_data[31:0]};
            default: load_data = 64'd0;
        endcase
    end
endmodule

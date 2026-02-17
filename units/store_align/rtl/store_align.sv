/*
 * Module: store_align
 * Purpose: Position store data and byte enables for RV64 store operations.
 * Interface: Source register data, byte offset, funct3 width selector, aligned write data/byte-enable outputs.
 * Behavior: Pure combinational lane placement for SB/SH/SW/SD.
 * Reset: Not applicable (combinational module).
 * Pipeline control: Not applicable.
 * Corner cases: Subword stores shift to addr[2:0] lane; invalid funct3 outputs zeros.
 */
module store_align (
    input  logic [63:0] rs2_data,
    input  logic [2:0]  addr_lsb,
    input  logic [2:0]  funct3,
    output logic [63:0] store_data,
    output logic [7:0]  byte_en
);
    import rv64_pkg::*;

    logic [5:0] shift_amt;

    assign shift_amt = {addr_lsb, 3'b000};

    always_comb begin
        store_data = 64'd0;
        byte_en = 8'd0;

        unique case (funct3)
            F3_SB: begin
                store_data = ({56'd0, rs2_data[7:0]} << shift_amt);
                byte_en = (8'h01 << addr_lsb);
            end

            F3_SH: begin
                store_data = ({48'd0, rs2_data[15:0]} << shift_amt);
                byte_en = (8'h03 << addr_lsb);
            end

            F3_SW: begin
                store_data = ({32'd0, rs2_data[31:0]} << shift_amt);
                byte_en = (8'h0F << addr_lsb);
            end

            F3_SD: begin
                store_data = rs2_data;
                byte_en = 8'hFF;
            end

            default: begin
                store_data = 64'd0;
                byte_en = 8'd0;
            end
        endcase
    end
endmodule

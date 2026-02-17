/*
 * Module: mul_unit
 * Purpose: Compute RV64 M-extension multiply-family results.
 * Interface: Decoded opcode/funct fields and operands in, valid/result out.
 * Behavior: Pure combinational datapath for MUL/MULH/MULHSU/MULHU/MULW.
 * Reset: Not applicable (combinational module).
 * Pipeline control: No internal state; caller determines instruction timing.
 * Corner cases: MULW uses only low 32-bit operands and sign-extends bit 31.
 */
module mul_unit (
    input  logic [6:0]  opcode,
    input  logic [2:0]  funct3,
    input  logic [6:0]  funct7,
    input  logic [63:0] rs1_data,
    input  logic [63:0] rs2_data,
    output logic        op_valid,
    output logic [63:0] result
);
    import rv64_pkg::*;

    logic signed [127:0] prod_ss;
    logic signed [129:0] prod_su;
    logic [127:0]        prod_uu;
    logic [63:0]         prod_w;

    assign prod_ss = $signed(rs1_data) * $signed(rs2_data);
    assign prod_su = $signed({rs1_data[63], rs1_data}) * $signed({1'b0, rs2_data});
    assign prod_uu = rs1_data * rs2_data;
    assign prod_w = rs1_data[31:0] * rs2_data[31:0];

    always_comb begin
        op_valid = 1'b0;
        result = 64'd0;

        if ((opcode == OP) && (funct7 == F7_M_EXT)) begin
            unique case (funct3)
                F3_ADD_SUB: begin
                    op_valid = 1'b1;
                    result = prod_uu[63:0];
                end

                F3_SLL: begin
                    op_valid = 1'b1;
                    result = prod_ss[127:64];
                end

                F3_SLT: begin
                    op_valid = 1'b1;
                    result = prod_su[127:64];
                end

                F3_SLTU: begin
                    op_valid = 1'b1;
                    result = prod_uu[127:64];
                end

                default: begin
                    op_valid = 1'b0;
                    result = 64'd0;
                end
            endcase
        end else if ((opcode == OP_32) &&
                     (funct7 == F7_M_EXT) &&
                     (funct3 == F3_ADD_SUB)) begin
            op_valid = 1'b1;
            result = {{32{prod_w[31]}}, prod_w[31:0]};
        end
    end
endmodule

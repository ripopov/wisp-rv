/*
 * Module: div_unit
 * Purpose: Compute RV64 M-extension divide/remainder-family results.
 * Interface: Decoded opcode/funct fields and operands in, valid/result out.
 * Behavior: Pure combinational datapath for DIV/DIVU/REM/REMU and W-suffix variants.
 * Reset: Not applicable (combinational module).
 * Pipeline control: No internal state; caller determines instruction timing.
 * Corner cases: Implements RISC-V divide-by-zero and signed-overflow rules without traps.
 */
module div_unit (
    input  logic [6:0]  opcode,
    input  logic [2:0]  funct3,
    input  logic [6:0]  funct7,
    input  logic [63:0] rs1_data,
    input  logic [63:0] rs2_data,
    output logic        op_valid,
    output logic [63:0] result
);
    import rv64_pkg::*;

    localparam logic [63:0] MIN_INT64 = 64'h8000_0000_0000_0000;
    localparam logic [31:0] MIN_INT32 = 32'h8000_0000;

    logic signed [63:0] rs1_s;
    logic signed [63:0] rs2_s;
    logic [63:0] rs1_u;
    logic [63:0] rs2_u;

    logic signed [31:0] rs1_w_s;
    logic signed [31:0] rs2_w_s;
    logic [31:0] rs1_w_u;
    logic [31:0] rs2_w_u;

    logic signed [31:0] divw_q;
    logic signed [31:0] remw_r;
    logic [31:0] divuw_q;
    logic [31:0] remuw_r;

    assign rs1_s = $signed(rs1_data);
    assign rs2_s = $signed(rs2_data);
    assign rs1_u = rs1_data;
    assign rs2_u = rs2_data;

    assign rs1_w_s = $signed(rs1_data[31:0]);
    assign rs2_w_s = $signed(rs2_data[31:0]);
    assign rs1_w_u = rs1_data[31:0];
    assign rs2_w_u = rs2_data[31:0];

    always_comb begin
        op_valid = 1'b0;
        result = 64'd0;

        divw_q = 32'sd0;
        remw_r = 32'sd0;
        divuw_q = 32'd0;
        remuw_r = 32'd0;

        if (funct7 == F7_M_EXT) begin
            if (opcode == OP) begin
                unique case (funct3)
                    F3_XOR: begin
                        op_valid = 1'b1;
                        if (rs2_u == 64'd0) begin
                            result = 64'hFFFF_FFFF_FFFF_FFFF;
                        end else if ((rs1_u == MIN_INT64) &&
                                     (rs2_u == 64'hFFFF_FFFF_FFFF_FFFF)) begin
                            result = MIN_INT64;
                        end else begin
                            result = $signed(rs1_s / rs2_s);
                        end
                    end

                    F3_SRL_SRA: begin
                        op_valid = 1'b1;
                        if (rs2_u == 64'd0) begin
                            result = 64'hFFFF_FFFF_FFFF_FFFF;
                        end else begin
                            result = rs1_u / rs2_u;
                        end
                    end

                    F3_OR: begin
                        op_valid = 1'b1;
                        if (rs2_u == 64'd0) begin
                            result = rs1_u;
                        end else if ((rs1_u == MIN_INT64) &&
                                     (rs2_u == 64'hFFFF_FFFF_FFFF_FFFF)) begin
                            result = 64'd0;
                        end else begin
                            result = $signed(rs1_s % rs2_s);
                        end
                    end

                    F3_AND: begin
                        op_valid = 1'b1;
                        if (rs2_u == 64'd0) begin
                            result = rs1_u;
                        end else begin
                            result = rs1_u % rs2_u;
                        end
                    end

                    default: begin
                        op_valid = 1'b0;
                        result = 64'd0;
                    end
                endcase
            end else if (opcode == OP_32) begin
                unique case (funct3)
                    F3_XOR: begin
                        op_valid = 1'b1;
                        if (rs2_w_u == 32'd0) begin
                            result = 64'hFFFF_FFFF_FFFF_FFFF;
                        end else if ((rs1_w_u == MIN_INT32) &&
                                     (rs2_w_u == 32'hFFFF_FFFF)) begin
                            result = 64'hFFFF_FFFF_8000_0000;
                        end else begin
                            divw_q = rs1_w_s / rs2_w_s;
                            result = {{32{divw_q[31]}}, divw_q};
                        end
                    end

                    F3_SRL_SRA: begin
                        op_valid = 1'b1;
                        if (rs2_w_u == 32'd0) begin
                            result = 64'hFFFF_FFFF_FFFF_FFFF;
                        end else begin
                            divuw_q = rs1_w_u / rs2_w_u;
                            result = {{32{divuw_q[31]}}, divuw_q};
                        end
                    end

                    F3_OR: begin
                        op_valid = 1'b1;
                        if (rs2_w_u == 32'd0) begin
                            result = {{32{rs1_w_u[31]}}, rs1_w_u};
                        end else if ((rs1_w_u == MIN_INT32) &&
                                     (rs2_w_u == 32'hFFFF_FFFF)) begin
                            result = 64'd0;
                        end else begin
                            remw_r = rs1_w_s % rs2_w_s;
                            result = {{32{remw_r[31]}}, remw_r};
                        end
                    end

                    F3_AND: begin
                        op_valid = 1'b1;
                        if (rs2_w_u == 32'd0) begin
                            result = {{32{rs1_w_u[31]}}, rs1_w_u};
                        end else begin
                            remuw_r = rs1_w_u % rs2_w_u;
                            result = {{32{remuw_r[31]}}, remuw_r};
                        end
                    end

                    default: begin
                        op_valid = 1'b0;
                        result = 64'd0;
                    end
                endcase
            end
        end
    end
endmodule

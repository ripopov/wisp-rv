/*
 * Module: instr_decoder
 * Purpose: Decode RV64I instruction class and detect illegal encodings.
 * Interface: 32-bit instruction input; field extraction, format, and illegal flag outputs.
 * Behavior: Purely combinational decode of opcode/funct combinations.
 * Reset: Not applicable (combinational module).
 * Pipeline control: Upstream/downstream control can treat illegal instructions as traps later.
 * Corner cases: RV64 OP-IMM shift-immediate decode uses instr[31:26] (not full funct7).
 */
module instr_decoder (
    input  logic [31:0] instr,
    output logic [6:0]  opcode,
    output logic [4:0]  rd,
    output logic [4:0]  rs1,
    output logic [4:0]  rs2,
    output logic [2:0]  funct3,
    output logic [6:0]  funct7,
    output rv64_pkg::instr_format_t instr_format,
    output logic        illegal_instr
);
    import rv64_pkg::*;

    logic is_valid;

    assign opcode = instr[6:0];
    assign rd = instr[11:7];
    assign funct3 = instr[14:12];
    assign rs1 = instr[19:15];
    assign rs2 = instr[24:20];
    assign funct7 = instr[31:25];

    always_comb begin
        instr_format = I_TYPE;
        is_valid = 1'b0;

        unique case (opcode)
            OP: begin
                instr_format = R_TYPE;
                unique case (funct3)
                    F3_ADD_SUB: is_valid = (funct7 == 7'b0000000) || (funct7 == 7'b0100000);
                    F3_SLL:     is_valid = (funct7 == 7'b0000000);
                    F3_SLT:     is_valid = (funct7 == 7'b0000000);
                    F3_SLTU:    is_valid = (funct7 == 7'b0000000);
                    F3_XOR:     is_valid = (funct7 == 7'b0000000);
                    F3_SRL_SRA: is_valid = (funct7 == 7'b0000000) || (funct7 == 7'b0100000);
                    F3_OR:      is_valid = (funct7 == 7'b0000000);
                    F3_AND:     is_valid = (funct7 == 7'b0000000);
                    default:    is_valid = 1'b0;
                endcase
            end

            OP_32: begin
                instr_format = R_TYPE;
                unique case (funct3)
                    F3_ADD_SUB: is_valid = (funct7 == 7'b0000000) || (funct7 == 7'b0100000);
                    F3_SLL:     is_valid = (funct7 == 7'b0000000);
                    F3_SRL_SRA: is_valid = (funct7 == 7'b0000000) || (funct7 == 7'b0100000);
                    default:    is_valid = 1'b0;
                endcase
            end

            OP_IMM: begin
                instr_format = I_TYPE;
                unique case (funct3)
                    F3_ADD_SUB,
                    F3_SLT,
                    F3_SLTU,
                    F3_XOR,
                    F3_OR,
                    F3_AND: is_valid = 1'b1;
                    F3_SLL: is_valid = (instr[31:26] == 6'b000000);
                    F3_SRL_SRA: is_valid = (instr[31:26] == 6'b000000) ||
                                           (instr[31:26] == 6'b010000);
                    default: is_valid = 1'b0;
                endcase
            end

            OP_IMM_32: begin
                instr_format = I_TYPE;
                unique case (funct3)
                    F3_ADD_SUB: is_valid = 1'b1;
                    F3_SLL:     is_valid = (funct7 == 7'b0000000);
                    F3_SRL_SRA: is_valid = (funct7 == 7'b0000000) || (funct7 == 7'b0100000);
                    default:    is_valid = 1'b0;
                endcase
            end

            LOAD: begin
                instr_format = I_TYPE;
                unique case (funct3)
                    F3_LB,
                    F3_LH,
                    F3_LW,
                    F3_LD,
                    F3_LBU,
                    F3_LHU,
                    F3_LWU: is_valid = 1'b1;
                    default: is_valid = 1'b0;
                endcase
            end

            STORE: begin
                instr_format = S_TYPE;
                unique case (funct3)
                    F3_SB,
                    F3_SH,
                    F3_SW,
                    F3_SD: is_valid = 1'b1;
                    default: is_valid = 1'b0;
                endcase
            end

            BRANCH: begin
                instr_format = B_TYPE;
                unique case (funct3)
                    F3_BEQ,
                    F3_BNE,
                    F3_BLT,
                    F3_BGE,
                    F3_BLTU,
                    F3_BGEU: is_valid = 1'b1;
                    default: is_valid = 1'b0;
                endcase
            end

            LUI: begin
                instr_format = U_TYPE;
                is_valid = 1'b1;
            end

            AUIPC: begin
                instr_format = U_TYPE;
                is_valid = 1'b1;
            end

            JAL: begin
                instr_format = J_TYPE;
                is_valid = 1'b1;
            end

            JALR: begin
                instr_format = I_TYPE;
                is_valid = (funct3 == F3_ADD_SUB);
            end

            SYSTEM: begin
                instr_format = I_TYPE;
                if (funct3 == F3_SYSTEM_PRIV) begin
                    is_valid = (rd == 5'd0) &&
                               (rs1 == 5'd0) &&
                               ((instr[31:20] == SYSTEM_IMM_ECALL) ||
                                (instr[31:20] == SYSTEM_IMM_EBREAK) ||
                                (instr[31:20] == SYSTEM_IMM_MRET));
                end else begin
                    is_valid = (funct3 == F3_CSRRW) ||
                               (funct3 == F3_CSRRS) ||
                               (funct3 == F3_CSRRC) ||
                               (funct3 == F3_CSRRWI) ||
                               (funct3 == F3_CSRRSI) ||
                               (funct3 == F3_CSRRCI);
                end
            end

            FENCE: begin
                instr_format = I_TYPE;
                is_valid = (funct3 == F3_FENCE);
            end

            default: begin
                instr_format = I_TYPE;
                is_valid = 1'b0;
            end
        endcase
    end

    assign illegal_instr = ~is_valid;
endmodule

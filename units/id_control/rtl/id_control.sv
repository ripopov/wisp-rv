/*
 * Module: id_control
 * Purpose: Map decoded instruction fields into execute/memory/writeback control.
 * Interface: opcode/funct3/funct7 in, packed control bundle out.
 * Behavior: Pure combinational decode with safe-zero defaults for illegal patterns.
 * Reset: Not applicable (combinational module).
 * Pipeline control: Produces branch/jump/memory/reg-write intent for downstream stages.
 * Corner cases: RV64 OP-IMM shift forms validate funct7[6:1] so shamt[5] remains legal.
 */
module id_control (
    input  logic [6:0] opcode,
    input  logic [2:0] funct3,
    input  logic [6:0] funct7,
    output rv64_pkg::id_ctrl_t ctrl
);
    import rv64_pkg::*;

    id_ctrl_t ctrl_next;
    logic valid;

    always_comb begin
        ctrl_next = '0;
        ctrl_next.alu_op = ALU_OP_ADD;
        ctrl_next.alu_src = ALU_SRC_REG;
        valid = 1'b1;

        unique case (opcode)
            OP: begin
                ctrl_next.reg_write = 1'b1;
                ctrl_next.alu_src = ALU_SRC_REG;
                unique case (funct3)
                    F3_ADD_SUB: begin
                        if (funct7 == 7'b0000000) begin
                            ctrl_next.alu_op = ALU_OP_ADD;
                        end else if (funct7 == 7'b0100000) begin
                            ctrl_next.alu_op = ALU_OP_SUB;
                        end else begin
                            valid = 1'b0;
                        end
                    end
                    F3_SLL: begin
                        if (funct7 == 7'b0000000) begin
                            ctrl_next.alu_op = ALU_OP_SLL;
                        end else begin
                            valid = 1'b0;
                        end
                    end
                    F3_SLT: begin
                        if (funct7 == 7'b0000000) begin
                            ctrl_next.alu_op = ALU_OP_SLT;
                        end else begin
                            valid = 1'b0;
                        end
                    end
                    F3_SLTU: begin
                        if (funct7 == 7'b0000000) begin
                            ctrl_next.alu_op = ALU_OP_SLTU;
                        end else begin
                            valid = 1'b0;
                        end
                    end
                    F3_XOR: begin
                        if (funct7 == 7'b0000000) begin
                            ctrl_next.alu_op = ALU_OP_XOR;
                        end else begin
                            valid = 1'b0;
                        end
                    end
                    F3_SRL_SRA: begin
                        if (funct7 == 7'b0000000) begin
                            ctrl_next.alu_op = ALU_OP_SRL;
                        end else if (funct7 == 7'b0100000) begin
                            ctrl_next.alu_op = ALU_OP_SRA;
                        end else begin
                            valid = 1'b0;
                        end
                    end
                    F3_OR: begin
                        if (funct7 == 7'b0000000) begin
                            ctrl_next.alu_op = ALU_OP_OR;
                        end else begin
                            valid = 1'b0;
                        end
                    end
                    F3_AND: begin
                        if (funct7 == 7'b0000000) begin
                            ctrl_next.alu_op = ALU_OP_AND;
                        end else begin
                            valid = 1'b0;
                        end
                    end
                    default: valid = 1'b0;
                endcase
            end

            OP_32: begin
                ctrl_next.reg_write = 1'b1;
                ctrl_next.alu_src = ALU_SRC_REG;
                ctrl_next.is_word_op = 1'b1;
                unique case (funct3)
                    F3_ADD_SUB: begin
                        if (funct7 == 7'b0000000) begin
                            ctrl_next.alu_op = ALU_OP_ADD;
                        end else if (funct7 == 7'b0100000) begin
                            ctrl_next.alu_op = ALU_OP_SUB;
                        end else begin
                            valid = 1'b0;
                        end
                    end
                    F3_SLL: begin
                        if (funct7 == 7'b0000000) begin
                            ctrl_next.alu_op = ALU_OP_SLL;
                        end else begin
                            valid = 1'b0;
                        end
                    end
                    F3_SRL_SRA: begin
                        if (funct7 == 7'b0000000) begin
                            ctrl_next.alu_op = ALU_OP_SRL;
                        end else if (funct7 == 7'b0100000) begin
                            ctrl_next.alu_op = ALU_OP_SRA;
                        end else begin
                            valid = 1'b0;
                        end
                    end
                    default: valid = 1'b0;
                endcase
            end

            OP_IMM: begin
                ctrl_next.reg_write = 1'b1;
                ctrl_next.alu_src = ALU_SRC_IMM;
                unique case (funct3)
                    F3_ADD_SUB: ctrl_next.alu_op = ALU_OP_ADD;
                    F3_SLT:     ctrl_next.alu_op = ALU_OP_SLT;
                    F3_SLTU:    ctrl_next.alu_op = ALU_OP_SLTU;
                    F3_XOR:     ctrl_next.alu_op = ALU_OP_XOR;
                    F3_OR:      ctrl_next.alu_op = ALU_OP_OR;
                    F3_AND:     ctrl_next.alu_op = ALU_OP_AND;
                    F3_SLL: begin
                        if (funct7[6:1] == 6'b000000) begin
                            ctrl_next.alu_op = ALU_OP_SLL;
                        end else begin
                            valid = 1'b0;
                        end
                    end
                    F3_SRL_SRA: begin
                        if (funct7[6:1] == 6'b000000) begin
                            ctrl_next.alu_op = ALU_OP_SRL;
                        end else if (funct7[6:1] == 6'b010000) begin
                            ctrl_next.alu_op = ALU_OP_SRA;
                        end else begin
                            valid = 1'b0;
                        end
                    end
                    default: valid = 1'b0;
                endcase
            end

            OP_IMM_32: begin
                ctrl_next.reg_write = 1'b1;
                ctrl_next.alu_src = ALU_SRC_IMM;
                ctrl_next.is_word_op = 1'b1;
                unique case (funct3)
                    F3_ADD_SUB: ctrl_next.alu_op = ALU_OP_ADD;
                    F3_SLL: begin
                        if (funct7 == 7'b0000000) begin
                            ctrl_next.alu_op = ALU_OP_SLL;
                        end else begin
                            valid = 1'b0;
                        end
                    end
                    F3_SRL_SRA: begin
                        if (funct7 == 7'b0000000) begin
                            ctrl_next.alu_op = ALU_OP_SRL;
                        end else if (funct7 == 7'b0100000) begin
                            ctrl_next.alu_op = ALU_OP_SRA;
                        end else begin
                            valid = 1'b0;
                        end
                    end
                    default: valid = 1'b0;
                endcase
            end

            LOAD: begin
                if ((funct3 == F3_LB) ||
                    (funct3 == F3_LH) ||
                    (funct3 == F3_LW) ||
                    (funct3 == F3_LD) ||
                    (funct3 == F3_LBU) ||
                    (funct3 == F3_LHU) ||
                    (funct3 == F3_LWU)) begin
                    ctrl_next.alu_op = ALU_OP_ADD;
                    ctrl_next.alu_src = ALU_SRC_IMM;
                    ctrl_next.mem_read = 1'b1;
                    ctrl_next.reg_write = 1'b1;
                    ctrl_next.mem_to_reg = 1'b1;
                end else begin
                    valid = 1'b0;
                end
            end

            STORE: begin
                if ((funct3 == F3_SB) ||
                    (funct3 == F3_SH) ||
                    (funct3 == F3_SW) ||
                    (funct3 == F3_SD)) begin
                    ctrl_next.alu_op = ALU_OP_ADD;
                    ctrl_next.alu_src = ALU_SRC_IMM;
                    ctrl_next.mem_write = 1'b1;
                end else begin
                    valid = 1'b0;
                end
            end

            BRANCH: begin
                if ((funct3 == F3_BEQ) ||
                    (funct3 == F3_BNE) ||
                    (funct3 == F3_BLT) ||
                    (funct3 == F3_BGE) ||
                    (funct3 == F3_BLTU) ||
                    (funct3 == F3_BGEU)) begin
                    ctrl_next.alu_op = ALU_OP_SUB;
                    ctrl_next.alu_src = ALU_SRC_REG;
                    ctrl_next.branch = 1'b1;
                end else begin
                    valid = 1'b0;
                end
            end

            LUI: begin
                ctrl_next.alu_op = ALU_OP_ADD;
                ctrl_next.alu_src = ALU_SRC_IMM;
                ctrl_next.reg_write = 1'b1;
            end

            AUIPC: begin
                ctrl_next.alu_op = ALU_OP_ADD;
                ctrl_next.alu_src = ALU_SRC_IMM;
                ctrl_next.reg_write = 1'b1;
            end

            JAL: begin
                ctrl_next.alu_op = ALU_OP_ADD;
                ctrl_next.alu_src = ALU_SRC_IMM;
                ctrl_next.reg_write = 1'b1;
                ctrl_next.jump = 1'b1;
            end

            JALR: begin
                if (funct3 == F3_ADD_SUB) begin
                    ctrl_next.alu_op = ALU_OP_ADD;
                    ctrl_next.alu_src = ALU_SRC_IMM;
                    ctrl_next.reg_write = 1'b1;
                    ctrl_next.jump = 1'b1;
                end else begin
                    valid = 1'b0;
                end
            end

            SYSTEM: begin
                if (funct3 == F3_SYSTEM_PRIV) begin
                    ctrl_next = '0;
                    ctrl_next.alu_op = ALU_OP_ADD;
                    ctrl_next.alu_src = ALU_SRC_REG;
                end else if ((funct3 == F3_CSRRW) ||
                             (funct3 == F3_CSRRS) ||
                             (funct3 == F3_CSRRC) ||
                             (funct3 == F3_CSRRWI) ||
                             (funct3 == F3_CSRRSI) ||
                             (funct3 == F3_CSRRCI)) begin
                    ctrl_next = '0;
                    ctrl_next.alu_op = ALU_OP_ADD;
                    ctrl_next.alu_src = ALU_SRC_REG;
                    ctrl_next.reg_write = 1'b1;
                end else begin
                    valid = 1'b0;
                end
            end

            FENCE: begin
                if (funct3 == F3_FENCE) begin
                    ctrl_next = '0;
                    ctrl_next.alu_op = ALU_OP_ADD;
                    ctrl_next.alu_src = ALU_SRC_REG;
                end else begin
                    valid = 1'b0;
                end
            end

            default: valid = 1'b0;
        endcase

        if (!valid) begin
            ctrl_next = '0;
            ctrl_next.alu_op = ALU_OP_ADD;
            ctrl_next.alu_src = ALU_SRC_REG;
        end
    end

    assign ctrl = ctrl_next;
endmodule

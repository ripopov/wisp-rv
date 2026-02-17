/*
 * Module: ex_stage
 * Purpose: Execute-stage datapath for ALU ops, branch resolution, and jump target/link generation.
 * Interface: ID/EX payload/control fields in; ALU result, redirect decision, and redirect target out.
 * Behavior: Pure combinational execute logic with one-cycle latency.
 * Reset: Not applicable (combinational module).
 * Pipeline control: Jump redirects have priority over conditional branch redirects.
 * Corner cases: W-suffix results are truncated to 32 bits and sign-extended to 64 bits.
 */
module ex_stage (
    input  logic [63:0] pc,
    input  logic [63:0] rs1_data,
    input  logic [63:0] rs2_data,
    input  logic [63:0] imm,
    input  logic [6:0]  opcode,
    input  logic [2:0]  funct3,
    input  logic [3:0]  alu_op,
    input  logic        alu_src,
    input  logic        branch,
    input  logic        jump,
    input  logic        is_word_op,
    output logic [63:0] alu_result,
    output logic        branch_taken,
    output logic [63:0] branch_target
);
    import rv64_pkg::*;

    logic [63:0] alu_a;
    logic [63:0] alu_b;
    logic [63:0] alu_b_eff;
    logic [63:0] alu_raw_result;
    logic        alu_zero;
    logic        branch_cond_taken;
    logic        jump_taken;
    logic [63:0] jump_target;
    logic [63:0] jump_link_addr;
    logic        is_jalr;

    assign is_jalr = (opcode == JALR);

    always_comb begin
        if (opcode == LUI) begin
            alu_a = 64'd0;
        end else if ((opcode == AUIPC) || (opcode == JAL) || (opcode == JALR)) begin
            alu_a = pc;
        end else begin
            alu_a = rs1_data;
        end

        if (jump) begin
            alu_b = 64'd4;
        end else if (alu_src == ALU_SRC_IMM) begin
            alu_b = imm;
        end else begin
            alu_b = rs2_data;
        end

        if (is_word_op &&
            ((alu_op == ALU_OP_SLL) ||
             (alu_op == ALU_OP_SRL) ||
             (alu_op == ALU_OP_SRA))) begin
            alu_b_eff = {59'd0, alu_b[4:0]};
        end else begin
            alu_b_eff = alu_b;
        end
    end

    alu u_alu (
        .a(alu_a),
        .b(alu_b_eff),
        .op(alu_op),
        .result(alu_raw_result),
        .zero(alu_zero)
    );

    branch_unit u_branch_unit (
        .rs1_data(rs1_data),
        .rs2_data(rs2_data),
        .funct3(funct3),
        .branch(branch),
        .branch_taken(branch_cond_taken)
    );

    jump_unit u_jump_unit (
        .pc(pc),
        .rs1_data(rs1_data),
        .imm(imm),
        .jump(jump),
        .is_jalr(is_jalr),
        .jump_taken(jump_taken),
        .jump_target(jump_target),
        .link_addr(jump_link_addr)
    );

    always_comb begin
        if (jump) begin
            alu_result = jump_link_addr;
        end else begin
            alu_result = alu_raw_result;
        end

        if (is_word_op) begin
            alu_result = {{32{alu_result[31]}}, alu_result[31:0]};
        end
    end

    always_comb begin
        if (jump_taken) begin
            branch_taken = 1'b1;
            branch_target = jump_target;
        end else begin
            branch_taken = branch_cond_taken;
            branch_target = pc + imm;
        end
    end
endmodule

/*
 * Module: jump_unit
 * Purpose: Compute jump redirect target and link address for JAL/JALR.
 * Interface: PC, rs1, immediate, jump enable, JALR selector, and computed outputs.
 * Behavior: Pure combinational jump target/link calculation.
 * Reset: Not applicable (combinational module).
 * Pipeline control: jump_taken mirrors jump enable and is used to trigger redirects.
 * Corner cases: JALR target masks bit 0 per spec: (rs1 + imm) & ~1.
 */
module jump_unit (
    input  logic [63:0] pc,
    input  logic [63:0] rs1_data,
    input  logic [63:0] imm,
    input  logic        jump,
    input  logic        is_jalr,
    output logic        jump_taken,
    output logic [63:0] jump_target,
    output logic [63:0] link_addr
);
    logic [63:0] jalr_sum;

    assign jalr_sum = rs1_data + imm;

    always_comb begin
        jump_taken = jump;
        link_addr = pc + 64'd4;

        if (is_jalr) begin
            jump_target = jalr_sum & 64'hFFFF_FFFF_FFFF_FFFE;
        end else begin
            jump_target = pc + imm;
        end
    end
endmodule

/*
 * Module: imm_gen
 * Purpose: Generate RV64 sign-extended immediates for decode/execute stages.
 * Interface: 32-bit instruction input plus decoded format; 64-bit immediate output.
 * Behavior: Purely combinational reconstruction of I/S/B/U/J immediates.
 * Reset: Not applicable (combinational module).
 * Pipeline control: No internal state; output follows input in same cycle.
 * Corner cases: U/J immediates are sign-extended to 64 bits (not zero-extended).
 */
module imm_gen (
    input  logic [31:0] instr,
    input  rv64_pkg::instr_format_t instr_format,
    output logic [63:0] imm
);
    import rv64_pkg::*;

    always_comb begin
        unique case (instr_format)
            I_TYPE: imm = {{52{instr[31]}}, instr[31:20]};

            S_TYPE: imm = {{52{instr[31]}}, instr[31:25], instr[11:7]};

            B_TYPE: imm = {{51{instr[31]}}, instr[31], instr[7], instr[30:25], instr[11:8], 1'b0};

            U_TYPE: imm = {{32{instr[31]}}, instr[31:12], 12'b0};

            J_TYPE: imm = {{43{instr[31]}}, instr[31], instr[19:12], instr[20], instr[30:21], 1'b0};

            default: imm = 64'd0;
        endcase
    end
endmodule

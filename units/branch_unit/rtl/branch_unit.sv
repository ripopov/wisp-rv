/*
 * Module: branch_unit
 * Purpose: Evaluate RV64 branch conditions for the execute stage.
 * Interface: rs1/rs2 operands, branch funct3 selector, branch enable, branch_taken output.
 * Behavior: Pure combinational compare logic with signed/unsigned modes per funct3.
 * Reset: Not applicable (combinational module).
 * Pipeline control: If branch enable is low, branch_taken is forced low.
 * Corner cases: BLT/BGE are signed compares; BLTU/BGEU are unsigned compares.
 */
module branch_unit (
    input  logic [63:0] rs1_data,
    input  logic [63:0] rs2_data,
    input  logic [2:0]  funct3,
    input  logic        branch,
    output logic        branch_taken
);
    import rv64_pkg::*;

    always_comb begin
        branch_taken = 1'b0;

        if (branch) begin
            unique case (funct3)
                F3_BEQ:  branch_taken = (rs1_data == rs2_data);
                F3_BNE:  branch_taken = (rs1_data != rs2_data);
                F3_BLT:  branch_taken = ($signed(rs1_data) < $signed(rs2_data));
                F3_BGE:  branch_taken = ($signed(rs1_data) >= $signed(rs2_data));
                F3_BLTU: branch_taken = (rs1_data < rs2_data);
                F3_BGEU: branch_taken = (rs1_data >= rs2_data);
                default: branch_taken = 1'b0;
            endcase
        end
    end
endmodule

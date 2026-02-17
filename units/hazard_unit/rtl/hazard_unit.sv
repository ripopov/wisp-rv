/*
 * Module: hazard_unit
 * Purpose: Detect decode-stage dependencies on EX-stage results that are only available at WB.
 * Interface: ID/EX producer metadata and IF/ID source register/opcode metadata in, load-use stall request out.
 * Behavior: Pure combinational hazard detection with source-use qualification by opcode.
 * Reset: Not applicable (combinational module).
 * Pipeline control: Requests one-cycle IF/ID stall plus ID/EX bubble insertion on load-use hazards.
 * Corner cases: Ignores x0 destinations and instructions that do not consume rs1/rs2.
 */
module hazard_unit (
    input  logic       id_ex_valid,
    input  logic       id_ex_mem_read,
    input  logic       id_ex_is_csr,
    input  logic [4:0] id_ex_rd,
    input  logic       if_id_valid,
    input  logic [6:0] if_id_opcode,
    input  logic [2:0] if_id_funct3,
    input  logic [4:0] if_id_rs1,
    input  logic [4:0] if_id_rs2,
    output logic       load_use_stall
);
    import rv64_pkg::*;

    logic if_id_uses_rs1;
    logic if_id_uses_rs2;
    logic rs1_hazard;
    logic rs2_hazard;
    logic producer_needs_wb;

    always_comb begin
        if_id_uses_rs1 = 1'b0;
        if_id_uses_rs2 = 1'b0;

        unique case (if_id_opcode)
            OP,
            OP_32,
            STORE,
            BRANCH: begin
                if_id_uses_rs1 = 1'b1;
                if_id_uses_rs2 = 1'b1;
            end

            OP_IMM,
            OP_IMM_32,
            LOAD,
            JALR: begin
                if_id_uses_rs1 = 1'b1;
            end

            SYSTEM: begin
                if ((if_id_funct3 == F3_CSRRW) ||
                    (if_id_funct3 == F3_CSRRS) ||
                    (if_id_funct3 == F3_CSRRC)) begin
                    if_id_uses_rs1 = 1'b1;
                end
            end

            default: begin
                if_id_uses_rs1 = 1'b0;
                if_id_uses_rs2 = 1'b0;
            end
        endcase

        rs1_hazard = if_id_uses_rs1 && (id_ex_rd == if_id_rs1);
        rs2_hazard = if_id_uses_rs2 && (id_ex_rd == if_id_rs2);

        producer_needs_wb = id_ex_mem_read || id_ex_is_csr;

        load_use_stall = id_ex_valid &&
                         producer_needs_wb &&
                         if_id_valid &&
                         (id_ex_rd != 5'd0) &&
                         (rs1_hazard || rs2_hazard);
    end
endmodule

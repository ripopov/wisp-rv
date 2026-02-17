/*
 * Module: pipeline_ctrl
 * Purpose: Initial global stall/flush/redirect control for Stage-06 pipeline integration.
 * Interface: EX redirect request and MEM-stage stall in; per-stage stall/flush and redirect outputs out.
 * Behavior: Pure combinational control with redirect and memory-stall handling.
 * Reset: Not applicable (combinational module).
 * Pipeline control: Redirect flushes IF/ID/EX-path younger instructions; memory stalls freeze upstream stages.
 * Corner cases: Redirect and memory-stall can assert together; flush still wins in pipeline register priority.
 */
module pipeline_ctrl (
    input  logic        ex_redirect_valid,
    input  logic [63:0] ex_redirect_pc,
    input  logic        mem_stall,

    output logic        if_stage_stall,
    output logic        if_stage_flush,
    output logic        if_id_stall,
    output logic        if_id_flush,
    output logic        id_ex_stall,
    output logic        id_ex_flush,
    output logic        ex_mem_stall,
    output logic        ex_mem_flush,
    output logic        mem_wb_stall,
    output logic        mem_wb_flush,

    output logic        redirect_valid,
    output logic [63:0] redirect_pc
);
    always_comb begin
        if_stage_stall = 1'b0;
        if_stage_flush = 1'b0;
        if_id_stall = 1'b0;
        if_id_flush = 1'b0;
        id_ex_stall = 1'b0;
        id_ex_flush = 1'b0;
        ex_mem_stall = 1'b0;
        ex_mem_flush = 1'b0;
        mem_wb_stall = 1'b0;
        mem_wb_flush = 1'b0;

        redirect_valid = ex_redirect_valid;
        redirect_pc = ex_redirect_pc;

        if (mem_stall) begin
            if_stage_stall = 1'b1;
            if_id_stall = 1'b1;
            id_ex_stall = 1'b1;
            ex_mem_stall = 1'b1;
        end

        if (ex_redirect_valid) begin
            if_stage_flush = 1'b1;
            if_id_flush = 1'b1;
            id_ex_flush = 1'b1;
        end
    end
endmodule

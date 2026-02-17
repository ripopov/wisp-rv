/*
 * Module: imem_if_tb_wrap
 * Purpose: Expose zero-latency and one-cycle imem_if variants for cocotb validation.
 * Interface: Shared fetch/memory stimulus inputs with split outputs for each variant.
 * Behavior: Instantiates two imem_if modules with ZERO_LATENCY set to 1 and 0.
 * Reset: Shared active-high synchronous reset to both instances.
 * Pipeline control: One-cycle instance limits to one outstanding request.
 * Corner cases: Enables direct side-by-side behavior comparison under identical stimulus.
 */
module imem_if_tb_wrap (
    input  logic        clk,
    input  logic        rst,
    input  logic        fetch_req,
    input  logic [63:0] fetch_addr,
    input  logic        mem_ready,
    input  logic [31:0] mem_rdata,

    output logic        z_imem_req,
    output logic [63:0] z_imem_addr,
    output logic [31:0] z_instr,
    output logic        z_instr_valid,

    output logic        o_imem_req,
    output logic [63:0] o_imem_addr,
    output logic [31:0] o_instr,
    output logic        o_instr_valid
);
    imem_if #(
        .ZERO_LATENCY(1'b1)
    ) u_imem_if_zero_latency (
        .clk(clk),
        .rst(rst),
        .fetch_req(fetch_req),
        .fetch_addr(fetch_addr),
        .mem_ready(mem_ready),
        .mem_rdata(mem_rdata),
        .imem_req(z_imem_req),
        .imem_addr(z_imem_addr),
        .instr(z_instr),
        .instr_valid(z_instr_valid)
    );

    imem_if #(
        .ZERO_LATENCY(1'b0)
    ) u_imem_if_one_cycle (
        .clk(clk),
        .rst(rst),
        .fetch_req(fetch_req),
        .fetch_addr(fetch_addr),
        .mem_ready(mem_ready),
        .mem_rdata(mem_rdata),
        .imem_req(o_imem_req),
        .imem_addr(o_imem_addr),
        .instr(o_instr),
        .instr_valid(o_instr_valid)
    );
endmodule

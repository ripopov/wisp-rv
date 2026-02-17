/*
 * Module: dmem_if_tb_wrap
 * Purpose: Test wrapper exposing zero-latency and one-cycle dmem_if variants.
 * Interface: Shared LSU/memory stimulus with split outputs for each variant.
 * Behavior: Instantiates two dmem_if modules with ZERO_LATENCY set to 1 and 0.
 * Reset: Shared active-high synchronous reset to both instances.
 * Pipeline control: One-cycle variant allows one outstanding read at a time.
 * Corner cases: Enables side-by-side verification under identical request patterns.
 */
module dmem_if_tb_wrap (
    input  logic        clk,
    input  logic        rst,
    input  logic        req_valid,
    input  logic        req_we,
    input  logic [63:0] req_addr,
    input  logic [63:0] req_wdata,
    input  logic [7:0]  req_byte_en,
    input  logic        mem_ready,
    input  logic [63:0] mem_rdata,

    output logic        z_dmem_req,
    output logic        z_dmem_we,
    output logic [63:0] z_dmem_addr,
    output logic [63:0] z_dmem_wdata,
    output logic [7:0]  z_dmem_byte_en,
    output logic        z_req_accepted,
    output logic        z_resp_valid,
    output logic [63:0] z_resp_rdata,

    output logic        o_dmem_req,
    output logic        o_dmem_we,
    output logic [63:0] o_dmem_addr,
    output logic [63:0] o_dmem_wdata,
    output logic [7:0]  o_dmem_byte_en,
    output logic        o_req_accepted,
    output logic        o_resp_valid,
    output logic [63:0] o_resp_rdata
);
    dmem_if #(
        .ZERO_LATENCY(1'b1)
    ) u_dmem_if_zero_latency (
        .clk(clk),
        .rst(rst),
        .req_valid(req_valid),
        .req_we(req_we),
        .req_addr(req_addr),
        .req_wdata(req_wdata),
        .req_byte_en(req_byte_en),
        .mem_ready(mem_ready),
        .mem_rdata(mem_rdata),
        .dmem_req(z_dmem_req),
        .dmem_we(z_dmem_we),
        .dmem_addr(z_dmem_addr),
        .dmem_wdata(z_dmem_wdata),
        .dmem_byte_en(z_dmem_byte_en),
        .req_accepted(z_req_accepted),
        .resp_valid(z_resp_valid),
        .resp_rdata(z_resp_rdata)
    );

    dmem_if #(
        .ZERO_LATENCY(1'b0)
    ) u_dmem_if_one_cycle (
        .clk(clk),
        .rst(rst),
        .req_valid(req_valid),
        .req_we(req_we),
        .req_addr(req_addr),
        .req_wdata(req_wdata),
        .req_byte_en(req_byte_en),
        .mem_ready(mem_ready),
        .mem_rdata(mem_rdata),
        .dmem_req(o_dmem_req),
        .dmem_we(o_dmem_we),
        .dmem_addr(o_dmem_addr),
        .dmem_wdata(o_dmem_wdata),
        .dmem_byte_en(o_dmem_byte_en),
        .req_accepted(o_req_accepted),
        .resp_valid(o_resp_valid),
        .resp_rdata(o_resp_rdata)
    );
endmodule

/*
 * Module: memory_subsystem
 * Purpose: Integrate core_top with deterministic split instruction/data RAMs for end-to-end simulation.
 * Interface: Exposes clock/reset, core debug outputs, and testbench sideband memory read/write controls.
 * Behavior: core_top instruction port drives an instruction RAM; data port drives a separate data RAM.
 * Reset: Active-high synchronous reset is forwarded to the core; RAM contents persist across reset.
 * Pipeline control: Memory wait states are produced by ram_model ready handshakes; no extra arbitration is required.
 * Corner cases: Program/data initialization is done from cocotb via hierarchical RAM access before releasing reset.
 */
module memory_subsystem #(
    parameter logic [63:0] RESET_VECTOR = 64'h0000_0000_0000_0000,
    parameter bit          DMEM_ZERO_LATENCY = 1'b0,
    parameter int unsigned MEM_DEPTH_WORDS = 4096,
    parameter int unsigned IMEM_LATENCY = 0,
    parameter int unsigned DMEM_LATENCY = 2,
    parameter string       MEM_INIT_FILE = ""
) (
    input  logic        clk,
    input  logic        rst,
    input  logic        tb_mem_wr_en,
    input  logic        tb_mem_is_data,
    input  logic [63:0] tb_mem_wr_addr,
    input  logic [63:0] tb_mem_wr_data,
    input  logic [7:0]  tb_mem_wr_be,
    input  logic [63:0] tb_mem_rd_addr,
    output logic [63:0] tb_mem_rd_data,
    output logic [63:0] dbg_if_pc,
    output logic        dbg_wb_valid,
    output logic [4:0]  dbg_wb_rd,
    output logic [63:0] dbg_wb_data
);
    logic        imem_ready;
    logic [31:0] imem_rdata;
    logic        imem_req;
    logic [63:0] imem_addr;

    logic        dmem_ready;
    logic [63:0] dmem_rdata;
    logic        dmem_req;
    logic        dmem_we;
    logic [63:0] dmem_addr;
    logic [63:0] dmem_wdata;
    logic [7:0]  dmem_byte_en;

    logic [63:0] tb_imem_rd_data;
    logic [63:0] tb_dmem_rd_data;

    logic [63:0] imem_unused_b_rdata;
    logic        imem_unused_b_ready;
    logic [31:0] dmem_unused_a_rdata;
    logic        dmem_unused_a_ready;

    core_top #(
        .RESET_VECTOR(RESET_VECTOR),
        .DMEM_ZERO_LATENCY(DMEM_ZERO_LATENCY)
    ) u_core_top (
        .clk(clk),
        .rst(rst),
        .imem_ready(imem_ready),
        .imem_rdata(imem_rdata),
        .imem_req(imem_req),
        .imem_addr(imem_addr),
        .dmem_ready(dmem_ready),
        .dmem_rdata(dmem_rdata),
        .dmem_req(dmem_req),
        .dmem_we(dmem_we),
        .dmem_addr(dmem_addr),
        .dmem_wdata(dmem_wdata),
        .dmem_byte_en(dmem_byte_en),
        .dbg_if_pc(dbg_if_pc),
        .dbg_wb_valid(dbg_wb_valid),
        .dbg_wb_rd(dbg_wb_rd),
        .dbg_wb_data(dbg_wb_data)
    );

    ram_model #(
        .DEPTH(MEM_DEPTH_WORDS),
        .ADDR_W(64),
        .INIT_FILE(MEM_INIT_FILE),
        .A_LATENCY(IMEM_LATENCY),
        .B_LATENCY(0)
    ) u_imem_ram (
        .clk(clk),
        .a_addr(imem_addr),
        .a_req(imem_req),
        .a_rdata(imem_rdata),
        .a_ready(imem_ready),
        .b_addr('0),
        .b_req(1'b0),
        .b_wr(1'b0),
        .b_wdata(64'd0),
        .b_be(8'd0),
        .b_rdata(imem_unused_b_rdata),
        .b_ready(imem_unused_b_ready),
        .tb_wr_en(tb_mem_wr_en && !tb_mem_is_data),
        .tb_wr_addr(tb_mem_wr_addr),
        .tb_wr_data(tb_mem_wr_data),
        .tb_wr_be(tb_mem_wr_be),
        .tb_rd_addr(tb_mem_rd_addr),
        .tb_rd_data(tb_imem_rd_data)
    );

    ram_model #(
        .DEPTH(MEM_DEPTH_WORDS),
        .ADDR_W(64),
        .INIT_FILE(""),
        .A_LATENCY(0),
        .B_LATENCY(DMEM_LATENCY)
    ) u_dmem_ram (
        .clk(clk),
        .a_addr('0),
        .a_req(1'b0),
        .a_rdata(dmem_unused_a_rdata),
        .a_ready(dmem_unused_a_ready),
        .b_addr(dmem_addr),
        .b_req(dmem_req),
        .b_wr(dmem_we),
        .b_wdata(dmem_wdata),
        .b_be(dmem_byte_en),
        .b_rdata(dmem_rdata),
        .b_ready(dmem_ready),
        .tb_wr_en(tb_mem_wr_en && tb_mem_is_data),
        .tb_wr_addr(tb_mem_wr_addr),
        .tb_wr_data(tb_mem_wr_data),
        .tb_wr_be(tb_mem_wr_be),
        .tb_rd_addr(tb_mem_rd_addr),
        .tb_rd_data(tb_dmem_rd_data)
    );

    assign tb_mem_rd_data = tb_mem_is_data ? tb_dmem_rd_data : tb_imem_rd_data;
endmodule

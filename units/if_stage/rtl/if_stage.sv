/*
 * Module: if_stage
 * Purpose: Maintain the fetch PC and issue instruction-memory fetches.
 * Interface: Stall/flush/redirect controls, instruction-memory ready/data inputs, PC/fetch outputs.
 * Behavior: Updates PC each cycle using pc_select and emits instruction/valid from imem_if.
 * Reset: Active-high synchronous reset sets PC to RESET_VECTOR and clears fetch validity.
 * Pipeline control: Redirect overrides stall for PC update; flush discards current fetch output.
 * Corner cases: PC is required to stay 4-byte aligned; sequential path increments by +4.
 */
module if_stage #(
    parameter logic [63:0] RESET_VECTOR = 64'h0000_0000_0000_0000
) (
    input  logic        clk,
    input  logic        rst,
    input  logic        stall,
    input  logic        flush,
    input  logic        redirect_valid,
    input  logic [63:0] redirect_pc,
    input  logic [31:0] imem_rdata,
    input  logic        imem_ready,
    output logic [63:0] pc,
    output logic [31:0] instr,
    output logic        instr_valid,
    output logic [63:0] imem_addr,
    output logic        imem_req
);
    localparam logic [31:0] NOP_INSTR = 32'h0000_0013;

    logic [63:0] pc_q;
    logic [63:0] next_pc;
    logic        hold_pc;
    logic        fetch_req;
    logic [31:0] fetch_instr;
    logic        fetch_instr_valid;

    assign hold_pc = stall || !imem_ready;
    assign fetch_req = !stall && imem_ready;

    pc_select u_pc_select (
        .current_pc(pc_q),
        .stall(hold_pc),
        .redirect_valid(redirect_valid),
        .redirect_pc(redirect_pc),
        .next_pc(next_pc)
    );

    imem_if #(
        .ZERO_LATENCY(1'b1)
    ) u_imem_if (
        .clk(clk),
        .rst(rst),
        .fetch_req(fetch_req),
        .fetch_addr(pc_q),
        .mem_ready(imem_ready),
        .mem_rdata(imem_rdata),
        .imem_req(imem_req),
        .imem_addr(imem_addr),
        .instr(fetch_instr),
        .instr_valid(fetch_instr_valid)
    );

    always_ff @(posedge clk) begin
        if (rst) begin
            pc_q <= RESET_VECTOR;
        end else begin
            pc_q <= next_pc;
        end
    end

    always_comb begin
        if (flush) begin
            instr = NOP_INSTR;
            instr_valid = 1'b0;
        end else begin
            instr = fetch_instr;
            instr_valid = fetch_instr_valid;
        end
    end

    assign pc = pc_q;

    always_comb begin
        assert (pc_q[1:0] == 2'b00)
            else $fatal(1, "if_stage PC misaligned: pc=0x%016h", pc_q);
        if (redirect_valid) begin
            assert (redirect_pc[1:0] == 2'b00)
                else $fatal(1, "if_stage redirect PC misaligned: redirect_pc=0x%016h", redirect_pc);
        end
    end
endmodule

/*
 * Module: ram_model
 * Purpose: Provide a deterministic dual-port simulation RAM for instruction and data accesses.
 * Interface: Port A serves instruction fetch reads; Port B serves data reads/writes with byte enables.
 * Behavior: Requests complete immediately when latency is zero, or after a fixed cycle delay when latency is non-zero.
 * Reset: Not required; memory/state are initialized deterministically at time zero.
 * Pipeline control: Backpressure is represented with ready deassertion until the configured latency expires.
 * Corner cases: Out-of-range accesses read as zero and ignore writes; little-endian byte-lane updates are enforced.
 */
module ram_model #(
    parameter int unsigned DEPTH = 4096,
    parameter int unsigned ADDR_W = 64,
    parameter string       INIT_FILE = "",
    parameter int unsigned A_LATENCY = 0,
    parameter int unsigned B_LATENCY = 0
) (
    input  logic              clk,

    // Port A (instruction fetch)
    input  logic [ADDR_W-1:0] a_addr,
    input  logic              a_req,
    output logic [31:0]       a_rdata,
    output logic              a_ready,

    // Port B (data)
    input  logic [ADDR_W-1:0] b_addr,
    input  logic              b_req,
    input  logic              b_wr,
    input  logic [63:0]       b_wdata,
    input  logic [7:0]        b_be,
    output logic [63:0]       b_rdata,
    output logic              b_ready,

    // Testbench sideband access (optional)
    input  logic              tb_wr_en,
    input  logic [ADDR_W-1:0] tb_wr_addr,
    input  logic [63:0]       tb_wr_data,
    input  logic [7:0]        tb_wr_be,
    input  logic [ADDR_W-1:0] tb_rd_addr,
    output logic [63:0]       tb_rd_data
);
    logic [63:0] mem [0:DEPTH-1];

    logic              a_pending_q;
    logic [31:0]       a_count_q;
    logic [ADDR_W-1:0] a_addr_q;

    logic              b_pending_q;
    logic [31:0]       b_count_q;
    logic [ADDR_W-1:0] b_addr_q;
    logic              b_wr_q;
    logic [63:0]       b_wdata_q;
    logic [7:0]        b_be_q;

    logic [ADDR_W-1:0] a_addr_use;
    logic [ADDR_W-1:0] b_addr_use;
    logic [63:0]       a_word;
    logic [63:0]       b_word;
    int unsigned       a_word_idx;
    int unsigned       b_word_idx;
    int unsigned       tb_word_idx;

    function automatic int unsigned addr_to_word_idx(input logic [ADDR_W-1:0] addr);
        addr_to_word_idx = int'(addr >> 3);
    endfunction

    function automatic logic idx_in_range(input int unsigned idx);
        idx_in_range = (idx < DEPTH);
    endfunction

    function automatic logic [63:0] merge_write_bytes(
        input logic [63:0] prior,
        input logic [63:0] wdata,
        input logic [7:0]  be
    );
        logic [63:0] merged;
        int i;
        begin
            merged = prior;
            for (i = 0; i < 8; i++) begin
                if (be[i]) begin
                    merged[(8*i) +: 8] = wdata[(8*i) +: 8];
                end
            end
            merge_write_bytes = merged;
        end
    endfunction

    initial begin : init_mem
        int i;
        assert (DEPTH > 0)
            else $fatal(1, "ram_model DEPTH must be > 0");

        for (i = 0; i < DEPTH; i++) begin
            mem[i] = 64'd0;
        end

        if (INIT_FILE != "") begin
            $readmemh(INIT_FILE, mem);
        end

        a_pending_q = 1'b0;
        a_count_q = 32'd0;
        a_addr_q = '0;

        b_pending_q = 1'b0;
        b_count_q = 32'd0;
        b_addr_q = '0;
        b_wr_q = 1'b0;
        b_wdata_q = 64'd0;
        b_be_q = 8'd0;
    end

    always_comb begin
        if (A_LATENCY == 0) begin
            a_ready = a_req;
            a_addr_use = a_addr;
        end else begin
            a_ready = a_pending_q && (a_count_q == 0);
            a_addr_use = a_pending_q ? a_addr_q : a_addr;
        end

        a_word_idx = addr_to_word_idx(a_addr_use);
        a_word = 64'd0;
        if (idx_in_range(a_word_idx)) begin
            a_word = mem[a_word_idx];
        end

        if (a_addr_use[2]) begin
            a_rdata = a_word[63:32];
        end else begin
            a_rdata = a_word[31:0];
        end
    end

    always_comb begin
        if (B_LATENCY == 0) begin
            b_ready = b_req;
            b_addr_use = b_addr;
        end else begin
            b_ready = b_pending_q && (b_count_q == 0);
            b_addr_use = b_pending_q ? b_addr_q : b_addr;
        end

        b_word_idx = addr_to_word_idx(b_addr_use);
        b_word = 64'd0;
        if (idx_in_range(b_word_idx)) begin
            b_word = mem[b_word_idx];
        end
        b_rdata = b_word;
    end

    always_comb begin
        tb_word_idx = addr_to_word_idx(tb_rd_addr);
        tb_rd_data = 64'd0;
        if (idx_in_range(tb_word_idx)) begin
            tb_rd_data = mem[tb_word_idx];
        end
    end

    always_ff @(posedge clk) begin
        if (tb_wr_en && idx_in_range(addr_to_word_idx(tb_wr_addr))) begin
            mem[addr_to_word_idx(tb_wr_addr)] <= merge_write_bytes(
                mem[addr_to_word_idx(tb_wr_addr)],
                tb_wr_data,
                tb_wr_be
            );
        end

        if (A_LATENCY != 0) begin
            if (a_pending_q) begin
                if (a_count_q == 0) begin
                    a_pending_q <= 1'b0;
                end else begin
                    a_count_q <= a_count_q - 1;
                end
            end else if (a_req) begin
                a_pending_q <= 1'b1;
                a_count_q <= A_LATENCY - 1;
                a_addr_q <= a_addr;
            end
        end

        if (!tb_wr_en) begin
            if (B_LATENCY == 0) begin
                if (b_req && b_wr && idx_in_range(addr_to_word_idx(b_addr))) begin
                    mem[addr_to_word_idx(b_addr)] <= merge_write_bytes(
                        mem[addr_to_word_idx(b_addr)],
                        b_wdata,
                        b_be
                    );
                end
            end else begin
                if (b_pending_q) begin
                    if (b_count_q == 0) begin
                        if (b_wr_q && idx_in_range(addr_to_word_idx(b_addr_q))) begin
                            mem[addr_to_word_idx(b_addr_q)] <= merge_write_bytes(
                                mem[addr_to_word_idx(b_addr_q)],
                                b_wdata_q,
                                b_be_q
                            );
                        end

                        b_pending_q <= 1'b0;
                    end else begin
                        b_count_q <= b_count_q - 1;
                    end
                end else if (b_req) begin
                    b_pending_q <= 1'b1;
                    b_count_q <= B_LATENCY - 1;
                    b_addr_q <= b_addr;
                    b_wr_q <= b_wr;
                    b_wdata_q <= b_wdata;
                    b_be_q <= b_be;
                end
            end
        end
    end
endmodule

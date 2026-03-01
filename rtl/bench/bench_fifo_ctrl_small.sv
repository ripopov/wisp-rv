module bench_fifo_ctrl_small (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       in_push,
    input  logic       in_pop,
    input  logic       in_flush,
    output logic [3:0] out_level,
    output logic       out_full,
    output logic       out_empty
);
    localparam int unsigned DEPTH = 8;

    logic in_push_q;
    logic in_pop_q;
    logic in_flush_q;
    logic [3:0] level_q;

    logic [3:0] level_d;
    logic full_d;
    logic empty_d;
    logic do_push;
    logic do_pop;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            in_push_q <= 1'b0;
            in_pop_q <= 1'b0;
            in_flush_q <= 1'b0;
            level_q <= '0;
            out_level <= '0;
            out_full <= 1'b0;
            out_empty <= 1'b1;
        end else begin
            in_push_q <= in_push;
            in_pop_q <= in_pop;
            in_flush_q <= in_flush;
            level_q <= level_d;
            out_level <= level_d;
            out_full <= full_d;
            out_empty <= empty_d;
        end
    end

    always_comb begin
        do_push = in_push_q && !in_flush_q && (level_q < DEPTH[3:0]);
        do_pop = in_pop_q && !in_flush_q && (level_q > '0);

        level_d = level_q;
        if (in_flush_q) begin
            level_d = '0;
        end else if (do_push && !do_pop) begin
            level_d = level_q + 4'd1;
        end else if (!do_push && do_pop) begin
            level_d = level_q - 4'd1;
        end

        full_d = (level_d == DEPTH[3:0]);
        empty_d = (level_d == '0);
    end
endmodule

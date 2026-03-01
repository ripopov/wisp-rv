module bench_cmp64_pipe (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [63:0] in_a,
    input  logic [63:0] in_b,
    input  logic [31:0] in_hi,
    input  logic [31:0] in_lo,
    output logic [31:0] out_y
);
    logic [63:0] a_q;
    logic [63:0] b_q;
    logic [31:0] hi_q;
    logic [31:0] lo_q;
    logic [31:0] cmp_d;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_q <= '0;
            b_q <= '0;
            hi_q <= '0;
            lo_q <= '0;
        end else begin
            a_q <= in_a;
            b_q <= in_b;
            hi_q <= in_hi;
            lo_q <= in_lo;
        end
    end

    always_comb begin
        if (a_q > b_q) begin
            cmp_d = hi_q;
        end else begin
            cmp_d = lo_q;
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_y <= '0;
        end else begin
            out_y <= cmp_d;
        end
    end
endmodule

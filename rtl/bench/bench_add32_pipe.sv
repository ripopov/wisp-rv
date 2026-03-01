module bench_add32_pipe (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [31:0] in_a,
    input  logic [31:0] in_b,
    output logic [31:0] out_y
);
    logic [31:0] in_a_q;
    logic [31:0] in_b_q;
    logic [31:0] sum_d;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            in_a_q <= '0;
            in_b_q <= '0;
        end else begin
            in_a_q <= in_a;
            in_b_q <= in_b;
        end
    end

    always_comb begin
        sum_d = in_a_q + in_b_q;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_y <= '0;
        end else begin
            out_y <= sum_d;
        end
    end
endmodule

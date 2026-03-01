module bench_mux8x32_pipe (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [2:0]  in_sel,
    input  logic [31:0] in_d0,
    input  logic [31:0] in_d1,
    input  logic [31:0] in_d2,
    input  logic [31:0] in_d3,
    input  logic [31:0] in_d4,
    input  logic [31:0] in_d5,
    input  logic [31:0] in_d6,
    input  logic [31:0] in_d7,
    output logic [31:0] out_y
);
    logic [2:0]  sel_q;
    logic [31:0] d0_q;
    logic [31:0] d1_q;
    logic [31:0] d2_q;
    logic [31:0] d3_q;
    logic [31:0] d4_q;
    logic [31:0] d5_q;
    logic [31:0] d6_q;
    logic [31:0] d7_q;
    logic [31:0] mux_d;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sel_q <= '0;
            d0_q <= '0;
            d1_q <= '0;
            d2_q <= '0;
            d3_q <= '0;
            d4_q <= '0;
            d5_q <= '0;
            d6_q <= '0;
            d7_q <= '0;
        end else begin
            sel_q <= in_sel;
            d0_q <= in_d0;
            d1_q <= in_d1;
            d2_q <= in_d2;
            d3_q <= in_d3;
            d4_q <= in_d4;
            d5_q <= in_d5;
            d6_q <= in_d6;
            d7_q <= in_d7;
        end
    end

    always_comb begin
        mux_d = '0;
        case (sel_q)
            3'd0: mux_d = d0_q;
            3'd1: mux_d = d1_q;
            3'd2: mux_d = d2_q;
            3'd3: mux_d = d3_q;
            3'd4: mux_d = d4_q;
            3'd5: mux_d = d5_q;
            3'd6: mux_d = d6_q;
            3'd7: mux_d = d7_q;
            default: mux_d = '0;
        endcase
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_y <= '0;
        end else begin
            out_y <= mux_d;
        end
    end
endmodule

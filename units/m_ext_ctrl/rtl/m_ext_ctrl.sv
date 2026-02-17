/*
 * Module: m_ext_ctrl
 * Purpose: Control M-extension timing for single-cycle multiply and multi-cycle divide.
 * Interface: EX-stage M-op classification and candidate results in, stall/result-valid outputs out.
 * Behavior: Multiplies retire immediately; divides hold EX for DIV_LATENCY cycles before releasing one result.
 * Reset: Active-high synchronous reset clears divide in-flight state.
 * Pipeline control: Asserts ex_busy_stall while a divide is in flight and deasserts on completion or flush.
 * Corner cases: Flush cancels in-flight divide and suppresses result emission.
 */
module m_ext_ctrl #(
    parameter int unsigned DIV_LATENCY = 8
) (
    input  logic        clk,
    input  logic        rst,
    input  logic        flush,

    input  logic        ex_valid,
    input  logic        ex_is_mul,
    input  logic        ex_is_div,
    input  logic [63:0] mul_result,
    input  logic [63:0] div_result,

    output logic        ex_busy_stall,
    output logic        m_result_valid,
    output logic [63:0] m_result
);
    localparam int unsigned DIV_COUNT_W = (DIV_LATENCY <= 1) ? 1 : $clog2(DIV_LATENCY);
    localparam logic [DIV_COUNT_W-1:0] DIV_LAST_COUNT = DIV_COUNT_W'(DIV_LATENCY - 1);

    logic div_busy_q;
    logic [DIV_COUNT_W-1:0] div_count_q;
    logic [63:0] div_result_q;

    logic start_div;
    logic div_done;

    initial begin
        assert (DIV_LATENCY >= 1)
            else $fatal(1, "m_ext_ctrl DIV_LATENCY must be >= 1");
    end

    assign start_div = ex_valid && ex_is_div && !div_busy_q && !flush;
    assign div_done = div_busy_q && (div_count_q == DIV_LAST_COUNT);

    always_comb begin
        ex_busy_stall = (start_div || div_busy_q) && !div_done;

        m_result_valid = 1'b0;
        m_result = 64'd0;

        if (div_busy_q) begin
            if (div_done) begin
                m_result_valid = 1'b1;
                m_result = div_result_q;
            end
        end else if (ex_valid && ex_is_mul) begin
            m_result_valid = 1'b1;
            m_result = mul_result;
        end
    end

    always_ff @(posedge clk) begin
        if (rst || flush) begin
            div_busy_q <= 1'b0;
            div_count_q <= '0;
            div_result_q <= 64'd0;
        end else if (start_div) begin
            div_busy_q <= 1'b1;
            div_count_q <= '0;
            div_result_q <= div_result;
        end else if (div_busy_q) begin
            if (div_done) begin
                div_busy_q <= 1'b0;
                div_count_q <= '0;
            end else begin
                div_count_q <= div_count_q + 1'b1;
            end
        end
    end
endmodule

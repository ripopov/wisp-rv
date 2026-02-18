/*
 * Module: m_ext_ctrl
 * Purpose: Coordinate EX-stage M-extension issue/stall timing.
 * Interface: EX-stage op classification and mul/div unit status/results in, start/stall/result mux outputs out.
 * Behavior: MUL retires immediately; DIV issues once, stalls EX until divider pulses result_valid, then releases one result.
 * Reset: Not applicable (combinational module).
 * Pipeline control: Asserts ex_busy_stall for active EX divide instructions while result is pending.
 * Corner cases: Flush suppresses issue, stall, and result emission for canceled instructions.
 */
module m_ext_ctrl (
    input  logic        flush,
    input  logic        ex_valid,
    input  logic        ex_is_mul,
    input  logic        ex_is_div,
    input  logic [63:0] mul_result,
    input  logic        div_busy,
    input  logic        div_result_valid,
    input  logic [63:0] div_result,
    output logic        div_start,
    output logic        ex_busy_stall,
    output logic        m_result_valid,
    output logic [63:0] m_result
);
    always_comb begin
        div_start = ex_valid &&
                    ex_is_div &&
                    !flush &&
                    !div_busy &&
                    !div_result_valid;

        ex_busy_stall = ex_valid &&
                        ex_is_div &&
                        !flush &&
                        !div_result_valid;

        m_result_valid = 1'b0;
        m_result = 64'd0;

        if (ex_valid && !flush) begin
            if (ex_is_mul) begin
                m_result_valid = 1'b1;
                m_result = mul_result;
            end else if (ex_is_div && div_result_valid) begin
                m_result_valid = 1'b1;
                m_result = div_result;
            end
        end
    end
endmodule

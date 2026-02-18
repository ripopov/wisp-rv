/*
 * Module: div_unit
 * Purpose: Execute RV64 M-extension divide/remainder operations with a radix-2 pipeline.
 * Interface: Decoded opcode/funct fields plus start/flush control in, busy/result-valid/result out.
 * Behavior: One radix-2 restoring-division iteration per cycle, with 64-cycle or 32-cycle word operation latency.
 * Reset: Active-high synchronous reset clears in-flight divide state.
 * Pipeline control: start latches one EX-stage divide op; busy holds while iterations run; result_valid pulses for one cycle on completion.
 * Corner cases: Implements RISC-V divide-by-zero and signed-overflow behavior without traps.
 */
module div_unit (
    input  logic        clk,
    input  logic        rst,
    input  logic        flush,
    input  logic        start,
    input  logic [6:0]  opcode,
    input  logic [2:0]  funct3,
    input  logic [6:0]  funct7,
    input  logic [63:0] rs1_data,
    input  logic [63:0] rs2_data,
    output logic        op_valid,
    output logic        busy,
    output logic        result_valid,
    output logic [63:0] result
);
    import rv64_pkg::*;

    localparam logic [63:0] MIN_INT64 = 64'h8000_0000_0000_0000;
    localparam logic [31:0] MIN_INT32 = 32'h8000_0000;

    logic signed [63:0] rs1_s;
    logic signed [63:0] rs2_s;
    logic [31:0] rs1_w_u;
    logic [31:0] rs2_w_u;
    logic signed [31:0] rs1_w_s;
    logic signed [31:0] rs2_w_s;

    logic op_is_word_d;
    logic op_is_signed_d;
    logic op_is_rem_d;

    logic start_fire;
    logic divisor_zero_d;
    logic signed_overflow_d;
    logic special_case_d;
    logic [63:0] special_result_d;
    logic dividend_neg_d;
    logic divisor_neg_d;
    logic [63:0] dividend_mag_d;
    logic [63:0] divisor_mag_d;
    logic [6:0]  iter_limit_d;
    logic [63:0] dividend_shift_init_d;

    logic busy_q;
    logic result_valid_q;
    logic [63:0] result_q;
    logic is_word_q;
    logic is_signed_q;
    logic is_rem_q;
    logic dividend_neg_q;
    logic divisor_neg_q;
    logic [63:0] divisor_mag_q;
    logic [63:0] dividend_shift_q;
    logic [64:0] remainder_q;
    logic [63:0] quotient_q;
    logic [6:0]  iter_limit_q;
    logic [6:0]  iter_count_q;
    logic special_case_q;
    logic [63:0] special_result_q;

    logic [64:0] remainder_trial;
    logic [64:0] remainder_next;
    logic [63:0] quotient_next;
    logic [63:0] dividend_shift_next;
    logic        quotient_bit_next;
    logic        final_cycle;
    logic [63:0] final_result;

    function automatic logic [63:0] sext32(input logic [31:0] value);
        sext32 = {{32{value[31]}}, value};
    endfunction

    function automatic logic [63:0] format_final_result(
        input logic        is_rem,
        input logic        is_signed,
        input logic        is_word,
        input logic        dividend_neg,
        input logic        divisor_neg,
        input logic [63:0] quotient_mag,
        input logic [63:0] remainder_mag
    );
        logic [63:0] raw_value;
        logic        negate_result;
    begin
        raw_value = is_rem ? remainder_mag : quotient_mag;

        negate_result = 1'b0;
        if (is_signed) begin
            if (is_rem) begin
                negate_result = dividend_neg;
            end else begin
                negate_result = dividend_neg ^ divisor_neg;
            end

            if (negate_result) begin
                raw_value = ~raw_value + 64'd1;
            end
        end

        if (is_word) begin
            format_final_result = sext32(raw_value[31:0]);
        end else begin
            format_final_result = raw_value;
        end
    end
    endfunction

    assign rs1_s = $signed(rs1_data);
    assign rs2_s = $signed(rs2_data);
    assign rs1_w_u = rs1_data[31:0];
    assign rs2_w_u = rs2_data[31:0];
    assign rs1_w_s = $signed(rs1_data[31:0]);
    assign rs2_w_s = $signed(rs2_data[31:0]);

    assign start_fire = start && op_valid && !busy_q && !flush;

    always_comb begin
        op_valid = 1'b0;
        op_is_word_d = 1'b0;
        op_is_signed_d = 1'b0;
        op_is_rem_d = 1'b0;

        if (funct7 == F7_M_EXT) begin
            if ((opcode == OP) || (opcode == OP_32)) begin
                unique case (funct3)
                    F3_XOR: begin
                        op_valid = 1'b1;
                        op_is_word_d = (opcode == OP_32);
                        op_is_signed_d = 1'b1;
                        op_is_rem_d = 1'b0;
                    end

                    F3_SRL_SRA: begin
                        op_valid = 1'b1;
                        op_is_word_d = (opcode == OP_32);
                        op_is_signed_d = 1'b0;
                        op_is_rem_d = 1'b0;
                    end

                    F3_OR: begin
                        op_valid = 1'b1;
                        op_is_word_d = (opcode == OP_32);
                        op_is_signed_d = 1'b1;
                        op_is_rem_d = 1'b1;
                    end

                    F3_AND: begin
                        op_valid = 1'b1;
                        op_is_word_d = (opcode == OP_32);
                        op_is_signed_d = 1'b0;
                        op_is_rem_d = 1'b1;
                    end

                    default: begin
                        op_valid = 1'b0;
                        op_is_word_d = 1'b0;
                        op_is_signed_d = 1'b0;
                        op_is_rem_d = 1'b0;
                    end
                endcase
            end
        end
    end

    always_comb begin
        divisor_zero_d = 1'b0;
        signed_overflow_d = 1'b0;
        special_case_d = 1'b0;
        special_result_d = 64'd0;

        dividend_neg_d = 1'b0;
        divisor_neg_d = 1'b0;
        dividend_mag_d = 64'd0;
        divisor_mag_d = 64'd0;

        iter_limit_d = 7'd64;
        dividend_shift_init_d = 64'd0;

        if (op_valid) begin
            if (op_is_word_d) begin
                divisor_zero_d = (rs2_w_u == 32'd0);
                signed_overflow_d = op_is_signed_d &&
                                    (rs1_w_u == MIN_INT32) &&
                                    (rs2_w_u == 32'hFFFF_FFFF);

                if (op_is_signed_d) begin
                    dividend_neg_d = (rs1_w_s < 0);
                    divisor_neg_d = (rs2_w_s < 0);
                    dividend_mag_d = {32'd0, (rs1_w_s < 0) ? (~rs1_w_u + 32'd1) : rs1_w_u};
                    divisor_mag_d = {32'd0, (rs2_w_s < 0) ? (~rs2_w_u + 32'd1) : rs2_w_u};
                end else begin
                    dividend_mag_d = {32'd0, rs1_w_u};
                    divisor_mag_d = {32'd0, rs2_w_u};
                end

                iter_limit_d = 7'd32;
                dividend_shift_init_d = dividend_mag_d << 6'd32;
            end else begin
                divisor_zero_d = (rs2_data == 64'd0);
                signed_overflow_d = op_is_signed_d &&
                                    (rs1_data == MIN_INT64) &&
                                    (rs2_data == 64'hFFFF_FFFF_FFFF_FFFF);

                if (op_is_signed_d) begin
                    dividend_neg_d = (rs1_s < 0);
                    divisor_neg_d = (rs2_s < 0);
                    dividend_mag_d = (rs1_s < 0) ? (~rs1_data + 64'd1) : rs1_data;
                    divisor_mag_d = (rs2_s < 0) ? (~rs2_data + 64'd1) : rs2_data;
                end else begin
                    dividend_mag_d = rs1_data;
                    divisor_mag_d = rs2_data;
                end

                iter_limit_d = 7'd64;
                dividend_shift_init_d = dividend_mag_d;
            end

            special_case_d = divisor_zero_d || signed_overflow_d;

            if (divisor_zero_d) begin
                if (op_is_rem_d) begin
                    if (op_is_word_d) begin
                        special_result_d = sext32(rs1_w_u);
                    end else begin
                        special_result_d = rs1_data;
                    end
                end else begin
                    special_result_d = 64'hFFFF_FFFF_FFFF_FFFF;
                end
            end else if (signed_overflow_d) begin
                if (op_is_rem_d) begin
                    special_result_d = 64'd0;
                end else if (op_is_word_d) begin
                    special_result_d = sext32(MIN_INT32);
                end else begin
                    special_result_d = MIN_INT64;
                end
            end
        end
    end

    always_comb begin
        remainder_trial = {remainder_q[63:0], dividend_shift_q[63]};
        dividend_shift_next = {dividend_shift_q[62:0], 1'b0};

        if (remainder_trial >= {1'b0, divisor_mag_q}) begin
            remainder_next = remainder_trial - {1'b0, divisor_mag_q};
            quotient_bit_next = 1'b1;
        end else begin
            remainder_next = remainder_trial;
            quotient_bit_next = 1'b0;
        end

        quotient_next = {quotient_q[62:0], quotient_bit_next};

        final_cycle = ((iter_count_q + 7'd1) >= iter_limit_q);
        final_result = format_final_result(
            is_rem_q,
            is_signed_q,
            is_word_q,
            dividend_neg_q,
            divisor_neg_q,
            quotient_next,
            remainder_next[63:0]
        );
    end

    always_ff @(posedge clk) begin
        if (rst || flush) begin
            busy_q <= 1'b0;
            result_valid_q <= 1'b0;
            result_q <= 64'd0;

            is_word_q <= 1'b0;
            is_signed_q <= 1'b0;
            is_rem_q <= 1'b0;
            dividend_neg_q <= 1'b0;
            divisor_neg_q <= 1'b0;

            divisor_mag_q <= 64'd0;
            dividend_shift_q <= 64'd0;
            remainder_q <= 65'd0;
            quotient_q <= 64'd0;
            iter_limit_q <= 7'd0;
            iter_count_q <= 7'd0;

            special_case_q <= 1'b0;
            special_result_q <= 64'd0;
        end else begin
            result_valid_q <= 1'b0;

            if (start_fire) begin
                busy_q <= 1'b1;

                is_word_q <= op_is_word_d;
                is_signed_q <= op_is_signed_d;
                is_rem_q <= op_is_rem_d;
                dividend_neg_q <= dividend_neg_d;
                divisor_neg_q <= divisor_neg_d;

                divisor_mag_q <= divisor_mag_d;
                dividend_shift_q <= dividend_shift_init_d;
                remainder_q <= 65'd0;
                quotient_q <= 64'd0;
                iter_limit_q <= special_case_d ? 7'd1 : iter_limit_d;
                iter_count_q <= 7'd0;

                special_case_q <= special_case_d;
                special_result_q <= special_result_d;
            end else if (busy_q) begin
                if (special_case_q) begin
                    busy_q <= 1'b0;
                    result_valid_q <= 1'b1;
                    result_q <= special_result_q;
                end else begin
                    dividend_shift_q <= dividend_shift_next;
                    remainder_q <= remainder_next;
                    quotient_q <= quotient_next;

                    if (final_cycle) begin
                        busy_q <= 1'b0;
                        result_valid_q <= 1'b1;
                        result_q <= final_result;
                        iter_count_q <= 7'd0;
                    end else begin
                        iter_count_q <= iter_count_q + 7'd1;
                    end
                end
            end
        end
    end

    assign busy = busy_q;
    assign result_valid = result_valid_q;
    assign result = result_q;
endmodule

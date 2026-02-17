module alu (
    input  logic [63:0] a,
    input  logic [63:0] b,
    input  logic [3:0]  op,
    output logic [63:0] result,
    output logic        zero
);
    always_comb begin
        unique case (op)
            4'h0: result = a + b;
            4'h1: result = a - b;
            4'h2: result = a & b;
            4'h3: result = a | b;
            4'h4: result = a ^ b;
            4'h5: result = ($signed(a) < $signed(b)) ? 64'd1 : 64'd0;
            4'h6: result = (a < b) ? 64'd1 : 64'd0;
            4'h7: result = a << b[5:0];
            4'h8: result = a >> b[5:0];
            4'h9: result = $signed(a) >>> b[5:0];
            default: result = 64'd0;
        endcase
    end

    assign zero = (result == 64'd0);
endmodule

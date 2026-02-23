module generic_sram_1rw #(
    parameter int DATA_WIDTH = 32,
    parameter int ADDR_WIDTH = 6
) (
    input  logic                  clk0,
    input  logic                  csb0,
    input  logic                  web0,
    input  logic [ADDR_WIDTH-1:0] addr0,
    input  logic [DATA_WIDTH-1:0] din0,
    output logic [DATA_WIDTH-1:0] dout0
);
    localparam int DEPTH = 1 << ADDR_WIDTH;

    logic                  csb0_q;
    logic                  web0_q;
    logic [ADDR_WIDTH-1:0] addr0_q;
    logic [DATA_WIDTH-1:0] din0_q;
    logic [DATA_WIDTH-1:0] mem [0:DEPTH-1];

    always_ff @(posedge clk0) begin
        csb0_q  <= csb0;
        web0_q  <= web0;
        addr0_q <= addr0;
        din0_q  <= din0;
    end

    always_ff @(negedge clk0) begin
        if (!csb0_q && !web0_q) begin
            mem[addr0_q] <= din0_q;
        end

        if (!csb0_q && web0_q) begin
            dout0 <= mem[addr0_q];
        end
    end
endmodule

module cache_data_sram_1rw (
    input  logic        clk0,
    input  logic        csb0,
    input  logic        web0,
    input  logic [5:0]  addr0,
    input  logic [31:0] din0,
    output logic [31:0] dout0
);
`ifdef USE_OPENRAM_MACROS
    sram_data_32x64_1rw u_mem (
        .clk0(clk0),
        .csb0(csb0),
        .web0(web0),
        .addr0(addr0),
        .din0(din0),
        .dout0(dout0)
    );
`else
    generic_sram_1rw #(
        .DATA_WIDTH(32),
        .ADDR_WIDTH(6)
    ) u_mem (
        .clk0(clk0),
        .csb0(csb0),
        .web0(web0),
        .addr0(addr0),
        .din0(din0),
        .dout0(dout0)
    );
`endif
endmodule

module cache_tag_sram_1rw (
    input  logic        clk0,
    input  logic        csb0,
    input  logic        web0,
    input  logic [5:0]  addr0,
    input  logic [23:0] din0,
    output logic [23:0] dout0
);
`ifdef USE_OPENRAM_MACROS
    sram_tag_24x64_1rw u_mem (
        .clk0(clk0),
        .csb0(csb0),
        .web0(web0),
        .addr0(addr0),
        .din0(din0),
        .dout0(dout0)
    );
`else
    generic_sram_1rw #(
        .DATA_WIDTH(24),
        .ADDR_WIDTH(6)
    ) u_mem (
        .clk0(clk0),
        .csb0(csb0),
        .web0(web0),
        .addr0(addr0),
        .din0(din0),
        .dout0(dout0)
    );
`endif
endmodule

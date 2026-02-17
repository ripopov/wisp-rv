/*
 * Module: dmem_if
 * Purpose: Adapt LSU requests to a simple ready/data data-memory interface.
 * Interface: LSU request signals in, memory bus signals out, request-accepted and response-valid status out.
 * Behavior: Zero-latency mode responds in request cycle; one-cycle mode supports one outstanding read.
 * Reset: Active-high synchronous reset clears pending one-cycle read state.
 * Pipeline control: Backpressure blocks request acceptance via req_accepted.
 * Corner cases: In one-cycle mode only reads produce delayed responses; writes complete on acceptance.
 */
module dmem_if #(
    parameter bit ZERO_LATENCY = 1'b0
) (
    input  logic        clk,
    input  logic        rst,
    input  logic        req_valid,
    input  logic        req_we,
    input  logic [63:0] req_addr,
    input  logic [63:0] req_wdata,
    input  logic [7:0]  req_byte_en,
    input  logic        mem_ready,
    input  logic [63:0] mem_rdata,
    output logic        dmem_req,
    output logic        dmem_we,
    output logic [63:0] dmem_addr,
    output logic [63:0] dmem_wdata,
    output logic [7:0]  dmem_byte_en,
    output logic        req_accepted,
    output logic        resp_valid,
    output logic [63:0] resp_rdata
);
    logic pending_read_q;
    logic req_fire;

    assign req_fire = dmem_req && mem_ready;

    always_ff @(posedge clk) begin
        if (rst) begin
            pending_read_q <= 1'b0;
        end else if (!ZERO_LATENCY) begin
            if (pending_read_q) begin
                pending_read_q <= 1'b0;
            end else if (req_fire && !req_we) begin
                pending_read_q <= 1'b1;
            end
        end
    end

    always_comb begin
        dmem_we = req_we;
        dmem_addr = req_addr;
        dmem_wdata = req_wdata;
        dmem_byte_en = req_byte_en;
        resp_rdata = mem_rdata;

        if (ZERO_LATENCY) begin
            dmem_req = req_valid;
            req_accepted = req_valid && mem_ready;
            resp_valid = req_valid && mem_ready && !req_we;
        end else begin
            dmem_req = req_valid && !pending_read_q;
            req_accepted = dmem_req && mem_ready;
            resp_valid = pending_read_q;
        end
    end
endmodule

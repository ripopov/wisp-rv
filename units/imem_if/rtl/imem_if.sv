/*
 * Module: imem_if
 * Purpose: Adapt IF fetch requests to a simple instruction-memory ready/data interface.
 * Interface: Fetch request/address in, memory ready/data in, memory request/address out, instruction/valid out.
 * Behavior: Zero-latency mode returns data in same cycle as accepted request; one-cycle mode returns one cycle later.
 * Reset: Active-high synchronous reset clears pending one-cycle requests.
 * Pipeline control: Supports one outstanding request in one-cycle mode; backpressure blocks new requests.
 * Corner cases: In one-cycle mode, response latency is fixed to one cycle after request acceptance.
 */
module imem_if #(
    parameter bit ZERO_LATENCY = 1'b1
) (
    input  logic        clk,
    input  logic        rst,
    input  logic        fetch_req,
    input  logic [63:0] fetch_addr,
    input  logic        mem_ready,
    input  logic [31:0] mem_rdata,
    output logic        imem_req,
    output logic [63:0] imem_addr,
    output logic [31:0] instr,
    output logic        instr_valid
);
    logic pending_q;
    logic req_fire;

    assign req_fire = fetch_req && mem_ready;

    always_ff @(posedge clk) begin
        if (rst) begin
            pending_q <= 1'b0;
        end else if (!ZERO_LATENCY) begin
            if (pending_q) begin
                pending_q <= 1'b0;
            end else if (req_fire) begin
                pending_q <= 1'b1;
            end
        end
    end

    always_comb begin
        imem_addr = fetch_addr;
        instr = mem_rdata;

        if (ZERO_LATENCY) begin
            imem_req = fetch_req;
            instr_valid = fetch_req && mem_ready;
        end else begin
            imem_req = fetch_req && !pending_q;
            instr_valid = pending_q;
        end
    end
endmodule

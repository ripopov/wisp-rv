/*
 * Module: lsu
 * Purpose: Generate load/store memory transactions and align load/store data.
 * Interface: Memory op controls/address/data in, memory handshake/data in, aligned outputs and stall/exception status out.
 * Behavior: Uses store_align/load_align and dmem_if to issue accesses and return aligned load data.
 * Reset: Active-high synchronous reset clears pending one-cycle load state.
 * Pipeline control: mem_stall stays high until the memory operation is accepted/completed.
 * Corner cases: Natural-alignment checks flag misaligned accesses and suppress memory requests.
 */
module lsu #(
    parameter bit DMEM_ZERO_LATENCY = 1'b0
) (
    input  logic        clk,
    input  logic        rst,
    input  logic        mem_read,
    input  logic        mem_write,
    input  logic [2:0]  funct3,
    input  logic [63:0] addr,
    input  logic [63:0] store_data_in,
    input  logic        dmem_ready,
    input  logic [63:0] dmem_rdata,
    output logic [63:0] load_data,
    output logic        load_valid,
    output logic        mem_stall,
    output logic        misaligned_access,
    output logic        dmem_req,
    output logic        dmem_we,
    output logic [63:0] dmem_addr,
    output logic [63:0] dmem_wdata,
    output logic [7:0]  dmem_byte_en
);
    import rv64_pkg::*;

    logic is_load;
    logic is_store;
    logic access;

    logic valid_load_funct3;
    logic valid_store_funct3;
    logic invalid_access;

    logic is_half_access;
    logic is_word_access;
    logic is_dword_access;
    logic alignment_mismatch;

    logic [63:0] aligned_store_data;
    logic [7:0]  aligned_byte_en;

    logic request_valid;
    logic request_we;
    logic req_accepted;
    logic resp_valid;
    logic [63:0] resp_rdata;

    logic pending_load_q;
    logic [2:0] pending_addr_lsb_q;
    logic [2:0] pending_funct3_q;
    logic [2:0] load_addr_lsb;
    logic [2:0] load_funct3;

    assign is_load = mem_read && !mem_write;
    assign is_store = mem_write && !mem_read;
    assign access = mem_read || mem_write;

    assign valid_load_funct3 = (funct3 == F3_LB)  ||
                               (funct3 == F3_LH)  ||
                               (funct3 == F3_LW)  ||
                               (funct3 == F3_LD)  ||
                               (funct3 == F3_LBU) ||
                               (funct3 == F3_LHU) ||
                               (funct3 == F3_LWU);

    assign valid_store_funct3 = (funct3 == F3_SB) ||
                                (funct3 == F3_SH) ||
                                (funct3 == F3_SW) ||
                                (funct3 == F3_SD);

    assign invalid_access = (mem_read && mem_write) ||
                            (mem_read && !valid_load_funct3) ||
                            (mem_write && !valid_store_funct3);

    assign is_half_access = (funct3 == F3_LH) ||
                            (funct3 == F3_LHU) ||
                            (funct3 == F3_SH);

    assign is_word_access = (funct3 == F3_LW) ||
                            (funct3 == F3_LWU) ||
                            (funct3 == F3_SW);

    assign is_dword_access = (funct3 == F3_LD) ||
                             (funct3 == F3_SD);

    assign alignment_mismatch = (is_half_access && (addr[0] != 1'b0)) ||
                                (is_word_access && (addr[1:0] != 2'b00)) ||
                                (is_dword_access && (addr[2:0] != 3'b000));

    assign misaligned_access = access && (invalid_access || alignment_mismatch);

    store_align u_store_align (
        .rs2_data(store_data_in),
        .addr_lsb(addr[2:0]),
        .funct3(funct3),
        .store_data(aligned_store_data),
        .byte_en(aligned_byte_en)
    );

    always_comb begin
        if (!DMEM_ZERO_LATENCY && pending_load_q) begin
            load_addr_lsb = pending_addr_lsb_q;
            load_funct3 = pending_funct3_q;
        end else begin
            load_addr_lsb = addr[2:0];
            load_funct3 = funct3;
        end
    end

    load_align u_load_align (
        .mem_rdata(resp_rdata),
        .addr_lsb(load_addr_lsb),
        .funct3(load_funct3),
        .load_data(load_data)
    );

    assign request_valid = access && !misaligned_access &&
                           (DMEM_ZERO_LATENCY || !pending_load_q);
    assign request_we = is_store;

    dmem_if #(
        .ZERO_LATENCY(DMEM_ZERO_LATENCY)
    ) u_dmem_if (
        .clk(clk),
        .rst(rst),
        .req_valid(request_valid),
        .req_we(request_we),
        .req_addr(addr),
        .req_wdata(aligned_store_data),
        .req_byte_en(aligned_byte_en),
        .mem_ready(dmem_ready),
        .mem_rdata(dmem_rdata),
        .dmem_req(dmem_req),
        .dmem_we(dmem_we),
        .dmem_addr(dmem_addr),
        .dmem_wdata(dmem_wdata),
        .dmem_byte_en(dmem_byte_en),
        .req_accepted(req_accepted),
        .resp_valid(resp_valid),
        .resp_rdata(resp_rdata)
    );

    always_ff @(posedge clk) begin
        if (rst) begin
            pending_load_q <= 1'b0;
            pending_addr_lsb_q <= 3'd0;
            pending_funct3_q <= 3'd0;
        end else if (!DMEM_ZERO_LATENCY) begin
            if (pending_load_q && resp_valid) begin
                pending_load_q <= 1'b0;
            end else if (!pending_load_q && req_accepted && is_load) begin
                pending_load_q <= 1'b1;
                pending_addr_lsb_q <= addr[2:0];
                pending_funct3_q <= funct3;
            end
        end
    end

    always_comb begin
        if (DMEM_ZERO_LATENCY) begin
            load_valid = resp_valid && is_load;
        end else begin
            load_valid = resp_valid && pending_load_q;
        end
    end

    always_comb begin
        mem_stall = 1'b0;

        if (!DMEM_ZERO_LATENCY && pending_load_q) begin
            mem_stall = !load_valid;
        end else if (is_store && !misaligned_access) begin
            mem_stall = !req_accepted;
        end else if (is_load && !misaligned_access) begin
            if (DMEM_ZERO_LATENCY) begin
                mem_stall = !req_accepted;
            end else begin
                mem_stall = !load_valid;
            end
        end
    end
endmodule

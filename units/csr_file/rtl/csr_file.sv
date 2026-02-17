/*
 * Module: csr_file
 * Purpose: Implement Stage-08 machine-mode CSR subset with counter support.
 * Interface: CSR request/commit ports, trap/mret update ports, and selected CSR state outputs.
 * Behavior: Combinational CSR reads with synchronous CSR/trap/counter updates.
 * Reset: Active-high synchronous reset clears writable CSRs and counters.
 * Pipeline control: Commit port applies one retired CSR instruction per cycle.
 * Corner cases: Read-only CSRs reject writes; mepc/mtvec are forced to 4-byte alignment.
 */
module csr_file (
    input  logic        clk,
    input  logic        rst,

    input  logic        csr_req_valid,
    input  logic [11:0] csr_req_addr,
    input  logic [2:0]  csr_req_cmd,
    input  logic [63:0] csr_req_wdata,
    output logic [63:0] csr_req_rdata,
    output logic        csr_req_illegal,

    input  logic        csr_commit_valid,
    input  logic [11:0] csr_commit_addr,
    input  logic [2:0]  csr_commit_cmd,
    input  logic [63:0] csr_commit_wdata,

    input  logic        trap_update_valid,
    input  logic [63:0] trap_mepc,
    input  logic [63:0] trap_mcause,
    input  logic [63:0] trap_mtval,
    input  logic [63:0] trap_mstatus_new,

    input  logic        mret_update_valid,
    input  logic [63:0] mret_mstatus_new,

    input  logic        inc_minstret,

    output logic [63:0] csr_mstatus,
    output logic [63:0] csr_mie,
    output logic [63:0] csr_mip,
    output logic [63:0] csr_mtvec,
    output logic [63:0] csr_mepc
);
    import rv64_pkg::*;

    localparam logic [11:0] CSR_MSTATUS   = 12'h300;
    localparam logic [11:0] CSR_MISA      = 12'h301;
    localparam logic [11:0] CSR_MIE       = 12'h304;
    localparam logic [11:0] CSR_MTVEC     = 12'h305;
    localparam logic [11:0] CSR_MSCRATCH  = 12'h340;
    localparam logic [11:0] CSR_MEPC      = 12'h341;
    localparam logic [11:0] CSR_MCAUSE    = 12'h342;
    localparam logic [11:0] CSR_MTVAL     = 12'h343;
    localparam logic [11:0] CSR_MIP       = 12'h344;
    localparam logic [11:0] CSR_MVENDORID = 12'hF11;
    localparam logic [11:0] CSR_MARCHID   = 12'hF12;
    localparam logic [11:0] CSR_MIMPID    = 12'hF13;
    localparam logic [11:0] CSR_MHARTID   = 12'hF14;
    localparam logic [11:0] CSR_MCYCLE    = 12'hB00;
    localparam logic [11:0] CSR_MINSTRET  = 12'hB02;

    localparam logic [63:0] MISA_RV64I = 64'h8000_0000_0000_0100;

    logic [63:0] mstatus_q;
    logic [63:0] mie_q;
    logic [63:0] mtvec_q;
    logic [63:0] mscratch_q;
    logic [63:0] mepc_q;
    logic [63:0] mcause_q;
    logic [63:0] mtval_q;
    logic [63:0] mip_q;
    logic [63:0] mcycle_q;
    logic [63:0] minstret_q;

    logic [63:0] mstatus_d;
    logic [63:0] mie_d;
    logic [63:0] mtvec_d;
    logic [63:0] mscratch_d;
    logic [63:0] mepc_d;
    logic [63:0] mcause_d;
    logic [63:0] mtval_d;
    logic [63:0] mip_d;
    logic [63:0] mcycle_d;
    logic [63:0] minstret_d;

    logic [63:0] csr_commit_old;
    logic [63:0] csr_commit_new;
    logic        csr_commit_write_req;
    logic        csr_commit_write_legal;
    logic        csr_req_write_req;

    function automatic logic csr_addr_supported(input logic [11:0] addr);
        unique case (addr)
            CSR_MSTATUS,
            CSR_MISA,
            CSR_MIE,
            CSR_MTVEC,
            CSR_MSCRATCH,
            CSR_MEPC,
            CSR_MCAUSE,
            CSR_MTVAL,
            CSR_MIP,
            CSR_MVENDORID,
            CSR_MARCHID,
            CSR_MIMPID,
            CSR_MHARTID,
            CSR_MCYCLE,
            CSR_MINSTRET: csr_addr_supported = 1'b1;
            default: csr_addr_supported = 1'b0;
        endcase
    endfunction

    function automatic logic csr_addr_read_only(input logic [11:0] addr);
        unique case (addr)
            CSR_MISA,
            CSR_MVENDORID,
            CSR_MARCHID,
            CSR_MIMPID,
            CSR_MHARTID: csr_addr_read_only = 1'b1;
            default: csr_addr_read_only = 1'b0;
        endcase
    endfunction

    function automatic logic csr_cmd_writes(
        input logic [2:0]  cmd,
        input logic [63:0] wdata
    );
        unique case (csr_cmd_t'(cmd))
            CSR_CMD_RW,
            CSR_CMD_RWI: csr_cmd_writes = 1'b1;

            CSR_CMD_RS,
            CSR_CMD_RSI,
            CSR_CMD_RC,
            CSR_CMD_RCI: csr_cmd_writes = (wdata != 64'd0);

            default: csr_cmd_writes = 1'b0;
        endcase
    endfunction

    function automatic logic [63:0] csr_apply_mask(
        input logic [11:0] addr,
        input logic [63:0] value
    );
        unique case (addr)
            CSR_MSTATUS: csr_apply_mask = value & MSTATUS_STAGE08_MASK;
            CSR_MTVEC: csr_apply_mask = {value[63:2], 2'b00};
            CSR_MEPC: csr_apply_mask = {value[63:2], 2'b00};
            default: csr_apply_mask = value;
        endcase
    endfunction

    function automatic logic [63:0] csr_read_data(input logic [11:0] addr);
        unique case (addr)
            CSR_MSTATUS: csr_read_data = mstatus_q;
            CSR_MISA: csr_read_data = MISA_RV64I;
            CSR_MIE: csr_read_data = mie_q;
            CSR_MTVEC: csr_read_data = mtvec_q;
            CSR_MSCRATCH: csr_read_data = mscratch_q;
            CSR_MEPC: csr_read_data = mepc_q;
            CSR_MCAUSE: csr_read_data = mcause_q;
            CSR_MTVAL: csr_read_data = mtval_q;
            CSR_MIP: csr_read_data = mip_q;
            CSR_MVENDORID,
            CSR_MARCHID,
            CSR_MIMPID,
            CSR_MHARTID: csr_read_data = 64'd0;
            CSR_MCYCLE: csr_read_data = mcycle_q;
            CSR_MINSTRET: csr_read_data = minstret_q;
            default: csr_read_data = 64'd0;
        endcase
    endfunction

    assign csr_req_rdata = csr_read_data(csr_req_addr);

    assign csr_req_write_req = csr_cmd_writes(csr_req_cmd, csr_req_wdata);
    assign csr_req_illegal = csr_req_valid &&
                             (!csr_addr_supported(csr_req_addr) ||
                              (csr_req_write_req && csr_addr_read_only(csr_req_addr)));

    always_comb begin
        mstatus_d = mstatus_q;
        mie_d = mie_q;
        mtvec_d = mtvec_q;
        mscratch_d = mscratch_q;
        mepc_d = mepc_q;
        mcause_d = mcause_q;
        mtval_d = mtval_q;
        mip_d = mip_q;
        mcycle_d = mcycle_q;
        minstret_d = minstret_q;

        csr_commit_old = csr_read_data(csr_commit_addr);
        csr_commit_new = csr_commit_old;
        csr_commit_write_req = csr_cmd_writes(csr_commit_cmd, csr_commit_wdata);
        csr_commit_write_legal = csr_commit_write_req &&
                                 csr_addr_supported(csr_commit_addr) &&
                                 !csr_addr_read_only(csr_commit_addr);

        if (csr_commit_write_legal && csr_commit_valid) begin
            unique case (csr_cmd_t'(csr_commit_cmd))
                CSR_CMD_RW,
                CSR_CMD_RWI: csr_commit_new = csr_commit_wdata;

                CSR_CMD_RS,
                CSR_CMD_RSI: csr_commit_new = csr_commit_old | csr_commit_wdata;

                CSR_CMD_RC,
                CSR_CMD_RCI: csr_commit_new = csr_commit_old & ~csr_commit_wdata;

                default: csr_commit_new = csr_commit_old;
            endcase

            csr_commit_new = csr_apply_mask(csr_commit_addr, csr_commit_new);

            unique case (csr_commit_addr)
                CSR_MSTATUS: mstatus_d = csr_commit_new;
                CSR_MIE: mie_d = csr_commit_new;
                CSR_MTVEC: mtvec_d = csr_commit_new;
                CSR_MSCRATCH: mscratch_d = csr_commit_new;
                CSR_MEPC: mepc_d = csr_commit_new;
                CSR_MCAUSE: mcause_d = csr_commit_new;
                CSR_MTVAL: mtval_d = csr_commit_new;
                CSR_MIP: mip_d = csr_commit_new;
                CSR_MCYCLE: mcycle_d = csr_commit_new;
                CSR_MINSTRET: minstret_d = csr_commit_new;
                default: begin
                    mstatus_d = mstatus_d;
                end
            endcase
        end

        if (trap_update_valid) begin
            mstatus_d = trap_mstatus_new & MSTATUS_STAGE08_MASK;
            mepc_d = {trap_mepc[63:2], 2'b00};
            mcause_d = trap_mcause;
            mtval_d = trap_mtval;
        end

        if (mret_update_valid) begin
            mstatus_d = mret_mstatus_new & MSTATUS_STAGE08_MASK;
        end

        mcycle_d = mcycle_d + 64'd1;

        if (inc_minstret) begin
            minstret_d = minstret_d + 64'd1;
        end
    end

    always_ff @(posedge clk) begin
        if (rst) begin
            mstatus_q <= 64'd0;
            mie_q <= 64'd0;
            mtvec_q <= 64'd0;
            mscratch_q <= 64'd0;
            mepc_q <= 64'd0;
            mcause_q <= 64'd0;
            mtval_q <= 64'd0;
            mip_q <= 64'd0;
            mcycle_q <= 64'd0;
            minstret_q <= 64'd0;
        end else begin
            mstatus_q <= mstatus_d;
            mie_q <= mie_d;
            mtvec_q <= mtvec_d;
            mscratch_q <= mscratch_d;
            mepc_q <= mepc_d;
            mcause_q <= mcause_d;
            mtval_q <= mtval_d;
            mip_q <= mip_d;
            mcycle_q <= mcycle_d;
            minstret_q <= minstret_d;
        end
    end

    assign csr_mstatus = mstatus_q;
    assign csr_mie = mie_q;
    assign csr_mip = mip_q;
    assign csr_mtvec = mtvec_q;
    assign csr_mepc = mepc_q;
endmodule

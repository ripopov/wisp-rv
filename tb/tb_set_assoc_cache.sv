`timescale 1ns/1ps

module tb_set_assoc_cache;
    logic clk;
    logic rst_n;

    logic        req_valid;
    logic        req_ready;
    logic        req_write;
    logic [31:0] req_addr;
    logic [31:0] req_wdata;
    logic [3:0]  req_wmask;

    logic        resp_valid;
    logic        resp_hit;
    logic [31:0] resp_rdata;

    set_assoc_cache_2way dut (
        .clk(clk),
        .rst_n(rst_n),
        .req_valid(req_valid),
        .req_ready(req_ready),
        .req_write(req_write),
        .req_addr(req_addr),
        .req_wdata(req_wdata),
        .req_wmask(req_wmask),
        .resp_valid(resp_valid),
        .resp_hit(resp_hit),
        .resp_rdata(resp_rdata)
    );

    always #5 clk = ~clk;

    task automatic send_req(
        input logic        is_write,
        input logic [31:0] addr,
        input logic [31:0] wdata,
        input logic [3:0]  wmask
    );
        begin
            @(posedge clk);
            while (!req_ready) begin
                @(posedge clk);
            end

            req_valid <= 1'b1;
            req_write <= is_write;
            req_addr  <= addr;
            req_wdata <= wdata;
            req_wmask <= wmask;

            @(posedge clk);
            req_valid <= 1'b0;
            req_write <= 1'b0;
            req_addr  <= '0;
            req_wdata <= '0;
            req_wmask <= '0;
        end
    endtask

    task automatic wait_resp(
        output logic hit,
        output logic [31:0] rdata
    );
        begin
            @(posedge clk);
            while (!resp_valid) begin
                @(posedge clk);
            end
            hit = resp_hit;
            rdata = resp_rdata;
        end
    endtask

    logic hit;
    logic [31:0] rdata;

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;

        req_valid = 1'b0;
        req_write = 1'b0;
        req_addr = '0;
        req_wdata = '0;
        req_wmask = '0;

        repeat (4) @(posedge clk);
        rst_n = 1'b1;

        send_req(1'b0, 32'h0000_0010, 32'h0000_0000, 4'h0);
        wait_resp(hit, rdata);
        if (hit !== 1'b0) begin
            $fatal(1, "Expected read miss for empty cache");
        end

        send_req(1'b1, 32'h0000_0010, 32'hDEAD_BEEF, 4'hF);
        wait_resp(hit, rdata);
        if (hit !== 1'b0) begin
            $fatal(1, "Expected write miss and allocation");
        end

        send_req(1'b0, 32'h0000_0010, 32'h0000_0000, 4'h0);
        wait_resp(hit, rdata);
        if (hit !== 1'b1 || rdata !== 32'hDEAD_BEEF) begin
            $fatal(1, "Expected read hit with DEADBEEF, got hit=%0d data=%h", hit, rdata);
        end

        send_req(1'b1, 32'h0000_0010, 32'h0000_AAAA, 4'b0011);
        wait_resp(hit, rdata);
        if (hit !== 1'b1) begin
            $fatal(1, "Expected write hit for existing line");
        end

        send_req(1'b0, 32'h0000_0010, 32'h0000_0000, 4'h0);
        wait_resp(hit, rdata);
        if (hit !== 1'b1 || rdata !== 32'hDEAD_AAAA) begin
            $fatal(1, "Expected masked write update to DEADAAAA, got %h", rdata);
        end

        send_req(1'b1, 32'h0000_0110, 32'h1234_5678, 4'hF);
        wait_resp(hit, rdata);
        if (hit !== 1'b0) begin
            $fatal(1, "Expected second tag in same set to allocate in other way");
        end

        send_req(1'b0, 32'h0000_0010, 32'h0000_0000, 4'h0);
        wait_resp(hit, rdata);
        if (hit !== 1'b1 || rdata !== 32'hDEAD_AAAA) begin
            $fatal(1, "Expected first line to remain present after 2-way fill");
        end

        send_req(1'b0, 32'h0000_0110, 32'h0000_0000, 4'h0);
        wait_resp(hit, rdata);
        if (hit !== 1'b1 || rdata !== 32'h1234_5678) begin
            $fatal(1, "Expected second line hit with 12345678");
        end

        $display("PASS: set_assoc_cache_2way behavioral test");
        repeat (4) @(posedge clk);
        $finish;
    end
endmodule

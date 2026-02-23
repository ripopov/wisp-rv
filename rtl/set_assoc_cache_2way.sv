module set_assoc_cache_2way #(
    parameter int ADDR_WIDTH = 32,
    parameter int DATA_WIDTH = 32,
    parameter int NUM_SETS   = 64
) (
    input  logic                      clk,
    input  logic                      rst_n,
    input  logic                      req_valid,
    output logic                      req_ready,
    input  logic                      req_write,
    input  logic [ADDR_WIDTH-1:0]     req_addr,
    input  logic [DATA_WIDTH-1:0]     req_wdata,
    input  logic [(DATA_WIDTH/8)-1:0] req_wmask,
    output logic                      resp_valid,
    output logic                      resp_hit,
    output logic [DATA_WIDTH-1:0]     resp_rdata
);
    localparam int LINE_OFFSET_BITS = 2;
    localparam int SET_BITS         = $clog2(NUM_SETS);
    localparam int TAG_WIDTH        = ADDR_WIDTH - LINE_OFFSET_BITS - SET_BITS;

    typedef enum logic [2:0] {
        S_IDLE,
        S_LOOKUP_CMD,
        S_LOOKUP_EVAL,
        S_WRITE_CMD,
        S_WRITE_RESP
    } state_t;

    state_t state_q;

    logic                  req_write_q;
    logic [ADDR_WIDTH-1:0] req_addr_q;
    logic [DATA_WIDTH-1:0] req_wdata_q;
    logic [DATA_WIDTH/8-1:0] req_wmask_q;

    logic [NUM_SETS-1:0] way0_valid_q;
    logic [NUM_SETS-1:0] way1_valid_q;
    logic [NUM_SETS-1:0] rr_way_q;

    logic [SET_BITS-1:0] req_set_idx;
    logic [TAG_WIDTH-1:0] req_tag;

    logic [DATA_WIDTH-1:0] data_way0_dout;
    logic [DATA_WIDTH-1:0] data_way1_dout;
    logic [TAG_WIDTH-1:0]  tag_way0_dout;
    logic [TAG_WIDTH-1:0]  tag_way1_dout;

    logic data_way0_csb0;
    logic data_way0_web0;
    logic [SET_BITS-1:0] data_way0_addr0;
    logic [DATA_WIDTH-1:0] data_way0_din0;

    logic data_way1_csb0;
    logic data_way1_web0;
    logic [SET_BITS-1:0] data_way1_addr0;
    logic [DATA_WIDTH-1:0] data_way1_din0;

    logic tag_way0_csb0;
    logic tag_way0_web0;
    logic [SET_BITS-1:0] tag_way0_addr0;
    logic [TAG_WIDTH-1:0] tag_way0_din0;

    logic tag_way1_csb0;
    logic tag_way1_web0;
    logic [SET_BITS-1:0] tag_way1_addr0;
    logic [TAG_WIDTH-1:0] tag_way1_din0;

    logic wr_way_q;
    logic wr_alloc_q;
    logic wr_hit_q;
    logic [SET_BITS-1:0] wr_set_q;
    logic [TAG_WIDTH-1:0] wr_tag_q;
    logic [DATA_WIDTH-1:0] wr_data_q;

    logic way0_hit;
    logic way1_hit;
    logic hit_any;
    logic selected_way;
    logic [DATA_WIDTH-1:0] hit_data;
    logic [DATA_WIDTH-1:0] merged_write_data;

    function automatic [DATA_WIDTH-1:0] apply_byte_mask(
        input [DATA_WIDTH-1:0] curr,
        input [DATA_WIDTH-1:0] wr,
        input [DATA_WIDTH/8-1:0] mask
    );
        integer b;
        begin
            apply_byte_mask = curr;
            for (b = 0; b < DATA_WIDTH / 8; b = b + 1) begin
                if (mask[b]) begin
                    apply_byte_mask[(8*b) +: 8] = wr[(8*b) +: 8];
                end
            end
        end
    endfunction

    assign req_ready = (state_q == S_IDLE);

    assign req_set_idx = req_addr_q[LINE_OFFSET_BITS + SET_BITS - 1:LINE_OFFSET_BITS];
    assign req_tag = req_addr_q[ADDR_WIDTH - 1:LINE_OFFSET_BITS + SET_BITS];

    assign way0_hit = way0_valid_q[req_set_idx] && (tag_way0_dout == req_tag);
    assign way1_hit = way1_valid_q[req_set_idx] && (tag_way1_dout == req_tag);
    assign hit_any = way0_hit || way1_hit;
    assign selected_way = way0_hit ? 1'b0 : (way1_hit ? 1'b1 : rr_way_q[req_set_idx]);
    assign hit_data = way0_hit ? data_way0_dout : data_way1_dout;
    assign merged_write_data = apply_byte_mask(hit_any ? hit_data : '0, req_wdata_q, req_wmask_q);

    always_comb begin
        data_way0_csb0 = 1'b1;
        data_way0_web0 = 1'b1;
        data_way0_addr0 = req_set_idx;
        data_way0_din0 = '0;

        data_way1_csb0 = 1'b1;
        data_way1_web0 = 1'b1;
        data_way1_addr0 = req_set_idx;
        data_way1_din0 = '0;

        tag_way0_csb0 = 1'b1;
        tag_way0_web0 = 1'b1;
        tag_way0_addr0 = req_set_idx;
        tag_way0_din0 = '0;

        tag_way1_csb0 = 1'b1;
        tag_way1_web0 = 1'b1;
        tag_way1_addr0 = req_set_idx;
        tag_way1_din0 = '0;

        case (state_q)
            S_LOOKUP_CMD: begin
                data_way0_csb0 = 1'b0;
                data_way0_web0 = 1'b1;
                data_way1_csb0 = 1'b0;
                data_way1_web0 = 1'b1;
                tag_way0_csb0 = 1'b0;
                tag_way0_web0 = 1'b1;
                tag_way1_csb0 = 1'b0;
                tag_way1_web0 = 1'b1;
            end

            S_WRITE_CMD: begin
                if (wr_way_q == 1'b0) begin
                    data_way0_csb0 = 1'b0;
                    data_way0_web0 = 1'b0;
                    data_way0_addr0 = wr_set_q;
                    data_way0_din0 = wr_data_q;

                    if (wr_alloc_q) begin
                        tag_way0_csb0 = 1'b0;
                        tag_way0_web0 = 1'b0;
                        tag_way0_addr0 = wr_set_q;
                        tag_way0_din0 = wr_tag_q;
                    end
                end else begin
                    data_way1_csb0 = 1'b0;
                    data_way1_web0 = 1'b0;
                    data_way1_addr0 = wr_set_q;
                    data_way1_din0 = wr_data_q;

                    if (wr_alloc_q) begin
                        tag_way1_csb0 = 1'b0;
                        tag_way1_web0 = 1'b0;
                        tag_way1_addr0 = wr_set_q;
                        tag_way1_din0 = wr_tag_q;
                    end
                end
            end

            default: begin
            end
        endcase
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state_q <= S_IDLE;

            req_write_q <= 1'b0;
            req_addr_q <= '0;
            req_wdata_q <= '0;
            req_wmask_q <= '0;

            wr_way_q <= 1'b0;
            wr_alloc_q <= 1'b0;
            wr_hit_q <= 1'b0;
            wr_set_q <= '0;
            wr_tag_q <= '0;
            wr_data_q <= '0;

            way0_valid_q <= '0;
            way1_valid_q <= '0;
            rr_way_q <= '0;

            resp_valid <= 1'b0;
            resp_hit <= 1'b0;
            resp_rdata <= '0;
        end else begin
            resp_valid <= 1'b0;

            case (state_q)
                S_IDLE: begin
                    if (req_valid) begin
                        req_write_q <= req_write;
                        req_addr_q <= req_addr;
                        req_wdata_q <= req_wdata;
                        req_wmask_q <= req_wmask;
                        state_q <= S_LOOKUP_CMD;
                    end
                end

                S_LOOKUP_CMD: begin
                    state_q <= S_LOOKUP_EVAL;
                end

                S_LOOKUP_EVAL: begin
                    if (req_write_q) begin
                        wr_way_q <= selected_way;
                        wr_alloc_q <= !hit_any;
                        wr_hit_q <= hit_any;
                        wr_set_q <= req_set_idx;
                        wr_tag_q <= req_tag;
                        wr_data_q <= merged_write_data;
                        state_q <= S_WRITE_CMD;
                    end else begin
                        resp_valid <= 1'b1;
                        resp_hit <= hit_any;
                        resp_rdata <= hit_any ? hit_data : '0;
                        state_q <= S_IDLE;
                    end
                end

                S_WRITE_CMD: begin
                    state_q <= S_WRITE_RESP;
                end

                S_WRITE_RESP: begin
                    if (wr_alloc_q) begin
                        if (wr_way_q == 1'b0) begin
                            way0_valid_q[wr_set_q] <= 1'b1;
                        end else begin
                            way1_valid_q[wr_set_q] <= 1'b1;
                        end
                        rr_way_q[wr_set_q] <= ~wr_way_q;
                    end

                    resp_valid <= 1'b1;
                    resp_hit <= wr_hit_q;
                    resp_rdata <= '0;
                    state_q <= S_IDLE;
                end

                default: begin
                    state_q <= S_IDLE;
                end
            endcase
        end
    end

    cache_data_sram_1rw u_data_way0 (
        .clk0(clk),
        .csb0(data_way0_csb0),
        .web0(data_way0_web0),
        .addr0(data_way0_addr0),
        .din0(data_way0_din0),
        .dout0(data_way0_dout)
    );

    cache_data_sram_1rw u_data_way1 (
        .clk0(clk),
        .csb0(data_way1_csb0),
        .web0(data_way1_web0),
        .addr0(data_way1_addr0),
        .din0(data_way1_din0),
        .dout0(data_way1_dout)
    );

    cache_tag_sram_1rw u_tag_way0 (
        .clk0(clk),
        .csb0(tag_way0_csb0),
        .web0(tag_way0_web0),
        .addr0(tag_way0_addr0),
        .din0(tag_way0_din0),
        .dout0(tag_way0_dout)
    );

    cache_tag_sram_1rw u_tag_way1 (
        .clk0(clk),
        .csb0(tag_way1_csb0),
        .web0(tag_way1_web0),
        .addr0(tag_way1_addr0),
        .din0(tag_way1_din0),
        .dout0(tag_way1_dout)
    );

endmodule

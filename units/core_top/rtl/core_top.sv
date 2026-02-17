/*
 * Module: core_top
 * Purpose: Integrate IF/ID/EX/MEM/WB pipeline stages into a Stage-06 RV64 core.
 * Interface: Clock/reset, instruction-memory and data-memory interfaces, plus debug writeback visibility.
 * Behavior: Single-issue in-order 5-stage pipeline without forwarding.
 * Reset: Active-high synchronous reset for stage state elements.
 * Pipeline control: Handles EX redirects and MEM stalls through pipeline_ctrl.
 * Corner cases: Redirect flushes younger IF/ID and ID/EX instructions; invalid bubbles are inert.
 */
module core_top #(
    parameter logic [63:0] RESET_VECTOR = 64'h0000_0000_0000_0000,
    parameter bit          DMEM_ZERO_LATENCY = 1'b0
) (
    input  logic        clk,
    input  logic        rst,

    // Instruction memory interface.
    input  logic        imem_ready,
    input  logic [31:0] imem_rdata,
    output logic        imem_req,
    output logic [63:0] imem_addr,

    // Data memory interface.
    input  logic        dmem_ready,
    input  logic [63:0] dmem_rdata,
    output logic        dmem_req,
    output logic        dmem_we,
    output logic [63:0] dmem_addr,
    output logic [63:0] dmem_wdata,
    output logic [7:0]  dmem_byte_en,

    // Debug visibility.
    output logic [63:0] dbg_if_pc,
    output logic        dbg_wb_valid,
    output logic [4:0]  dbg_wb_rd,
    output logic [63:0] dbg_wb_data
);
    import rv64_pkg::*;

    logic        if_stage_stall;
    logic        if_stage_flush;
    logic        if_id_stall;
    logic        if_id_flush;
    logic        id_ex_stall;
    logic        id_ex_flush;
    logic        ex_mem_stall;
    logic        ex_mem_flush;
    logic        mem_wb_stall;
    logic        mem_wb_flush;
    logic        redirect_valid;
    logic [63:0] redirect_pc;

    logic [63:0] if_pc;
    logic [31:0] if_instr;
    logic        if_valid;

    logic [63:0] id_pc;
    logic [31:0] id_instr;
    logic        id_valid;

    logic [6:0]  id_opcode;
    logic [4:0]  id_rd;
    logic [4:0]  id_rs1;
    logic [4:0]  id_rs2;
    logic [2:0]  id_funct3;
    logic [6:0]  id_funct7;
    instr_format_t id_format;
    logic        id_illegal;
    logic [63:0] id_imm;
    id_ctrl_t    id_ctrl_raw;
    id_ctrl_t    id_ctrl_masked;
    logic        id_issue_valid;
    logic [4:0]  id_rs1_addr;
    logic [4:0]  id_rs2_addr;
    logic [63:0] id_rs1_data;
    logic [63:0] id_rs2_data;

    logic [63:0] ex_pc;
    logic [63:0] ex_rs1_data;
    logic [63:0] ex_rs2_data;
    logic [63:0] ex_imm;
    logic [6:0]  ex_opcode;
    logic [4:0]  ex_rd;
    logic [4:0]  ex_rs1_addr;
    logic [4:0]  ex_rs2_addr;
    logic [2:0]  ex_funct3;
    logic [6:0]  ex_funct7;
    logic [3:0]  ex_alu_op;
    logic        ex_alu_src;
    logic        ex_mem_read;
    logic        ex_mem_write;
    logic        ex_reg_write;
    logic        ex_mem_to_reg;
    logic        ex_branch;
    logic        ex_jump;
    logic        ex_is_word_op;
    logic        ex_valid;

    logic [63:0] ex_alu_result;
    logic        ex_branch_taken_raw;
    logic [63:0] ex_branch_target_raw;
    logic        ex_redirect_valid;

    logic [63:0] mem_pc;
    logic [63:0] mem_alu_result;
    logic [63:0] mem_rs2_data;
    logic [4:0]  mem_rd;
    logic [2:0]  mem_funct3;
    logic        mem_mem_read;
    logic        mem_mem_write;
    logic        mem_reg_write;
    logic        mem_mem_to_reg;
    logic        mem_is_word_op;
    logic        mem_branch_taken;
    logic [63:0] mem_branch_target;
    logic        mem_valid;

    logic [63:0] lsu_load_data;
    logic        lsu_load_valid;
    logic        lsu_mem_stall;
    logic        lsu_misaligned_access;
    logic        mem_op_active;
    logic        mem_stage_complete;

    logic [63:0] wb_alu_result;
    logic [63:0] wb_mem_data;
    logic [4:0]  wb_rd;
    logic        wb_reg_write;
    logic        wb_mem_to_reg;
    logic        wb_valid;
    logic [1:0]  wb_sel;
    logic [63:0] wb_data;
    logic        wb_write_enable;

    if_stage #(
        .RESET_VECTOR(RESET_VECTOR)
    ) u_if_stage (
        .clk(clk),
        .rst(rst),
        .stall(if_stage_stall),
        .flush(if_stage_flush),
        .redirect_valid(redirect_valid),
        .redirect_pc(redirect_pc),
        .imem_rdata(imem_rdata),
        .imem_ready(imem_ready),
        .pc(if_pc),
        .instr(if_instr),
        .instr_valid(if_valid),
        .imem_addr(imem_addr),
        .imem_req(imem_req)
    );

    if_id_reg u_if_id_reg (
        .clk(clk),
        .rst(rst),
        .stall(if_id_stall),
        .flush(if_id_flush),
        .pc_in(if_pc),
        .instr_in(if_instr),
        .valid_in(if_valid),
        .pc_out(id_pc),
        .instr_out(id_instr),
        .valid_out(id_valid)
    );

    instr_decoder u_instr_decoder (
        .instr(id_instr),
        .opcode(id_opcode),
        .rd(id_rd),
        .rs1(id_rs1),
        .rs2(id_rs2),
        .funct3(id_funct3),
        .funct7(id_funct7),
        .instr_format(id_format),
        .illegal_instr(id_illegal)
    );

    imm_gen u_imm_gen (
        .instr(id_instr),
        .instr_format(id_format),
        .imm(id_imm)
    );

    id_control u_id_control (
        .opcode(id_opcode),
        .funct3(id_funct3),
        .funct7(id_funct7),
        .ctrl(id_ctrl_raw)
    );

    always_comb begin
        id_issue_valid = id_valid && !id_illegal;

        id_ctrl_masked = '0;
        id_ctrl_masked.alu_op = ALU_OP_ADD;
        id_ctrl_masked.alu_src = ALU_SRC_REG;

        if (id_issue_valid) begin
            id_ctrl_masked = id_ctrl_raw;
        end

        if (id_issue_valid) begin
            id_rs1_addr = id_rs1;
            id_rs2_addr = id_rs2;
        end else begin
            id_rs1_addr = 5'd0;
            id_rs2_addr = 5'd0;
        end
    end

    regfile u_regfile (
        .clk(clk),
        .rst(rst),
        .rs1_addr(id_rs1_addr),
        .rs2_addr(id_rs2_addr),
        .wr_en(wb_write_enable),
        .wr_addr(wb_rd),
        .wr_data(wb_data),
        .rs1_data(id_rs1_data),
        .rs2_data(id_rs2_data)
    );

    id_ex_reg u_id_ex_reg (
        .clk(clk),
        .rst(rst),
        .stall(id_ex_stall),
        .flush(id_ex_flush),
        .pc_in(id_pc),
        .rs1_data_in(id_rs1_data),
        .rs2_data_in(id_rs2_data),
        .imm_in(id_imm),
        .opcode_in(id_opcode),
        .rd_in(id_rd),
        .rs1_addr_in(id_rs1),
        .rs2_addr_in(id_rs2),
        .funct3_in(id_funct3),
        .funct7_in(id_funct7),
        .alu_op_in(id_ctrl_masked.alu_op),
        .alu_src_in(id_ctrl_masked.alu_src),
        .mem_read_in(id_ctrl_masked.mem_read),
        .mem_write_in(id_ctrl_masked.mem_write),
        .reg_write_in(id_ctrl_masked.reg_write),
        .mem_to_reg_in(id_ctrl_masked.mem_to_reg),
        .branch_in(id_ctrl_masked.branch),
        .jump_in(id_ctrl_masked.jump),
        .is_word_op_in(id_ctrl_masked.is_word_op),
        .valid_in(id_issue_valid),
        .pc_out(ex_pc),
        .rs1_data_out(ex_rs1_data),
        .rs2_data_out(ex_rs2_data),
        .imm_out(ex_imm),
        .opcode_out(ex_opcode),
        .rd_out(ex_rd),
        .rs1_addr_out(ex_rs1_addr),
        .rs2_addr_out(ex_rs2_addr),
        .funct3_out(ex_funct3),
        .funct7_out(ex_funct7),
        .alu_op_out(ex_alu_op),
        .alu_src_out(ex_alu_src),
        .mem_read_out(ex_mem_read),
        .mem_write_out(ex_mem_write),
        .reg_write_out(ex_reg_write),
        .mem_to_reg_out(ex_mem_to_reg),
        .branch_out(ex_branch),
        .jump_out(ex_jump),
        .is_word_op_out(ex_is_word_op),
        .valid_out(ex_valid)
    );

    ex_stage u_ex_stage (
        .pc(ex_pc),
        .rs1_data(ex_rs1_data),
        .rs2_data(ex_rs2_data),
        .imm(ex_imm),
        .opcode(ex_opcode),
        .funct3(ex_funct3),
        .alu_op(ex_alu_op),
        .alu_src(ex_alu_src),
        .branch(ex_branch),
        .jump(ex_jump),
        .is_word_op(ex_is_word_op),
        .alu_result(ex_alu_result),
        .branch_taken(ex_branch_taken_raw),
        .branch_target(ex_branch_target_raw)
    );

    assign ex_redirect_valid = ex_valid && ex_branch_taken_raw;

    ex_mem_reg u_ex_mem_reg (
        .clk(clk),
        .rst(rst),
        .stall(ex_mem_stall),
        .flush(ex_mem_flush),
        .pc_in(ex_pc),
        .alu_result_in(ex_alu_result),
        .rs2_data_in(ex_rs2_data),
        .rd_in(ex_rd),
        .funct3_in(ex_funct3),
        .mem_read_in(ex_mem_read),
        .mem_write_in(ex_mem_write),
        .reg_write_in(ex_reg_write),
        .mem_to_reg_in(ex_mem_to_reg),
        .is_word_op_in(ex_is_word_op),
        .branch_taken_in(ex_redirect_valid),
        .branch_target_in(ex_branch_target_raw),
        .valid_in(ex_valid),
        .pc_out(mem_pc),
        .alu_result_out(mem_alu_result),
        .rs2_data_out(mem_rs2_data),
        .rd_out(mem_rd),
        .funct3_out(mem_funct3),
        .mem_read_out(mem_mem_read),
        .mem_write_out(mem_mem_write),
        .reg_write_out(mem_reg_write),
        .mem_to_reg_out(mem_mem_to_reg),
        .is_word_op_out(mem_is_word_op),
        .branch_taken_out(mem_branch_taken),
        .branch_target_out(mem_branch_target),
        .valid_out(mem_valid)
    );

    lsu #(
        .DMEM_ZERO_LATENCY(DMEM_ZERO_LATENCY)
    ) u_lsu (
        .clk(clk),
        .rst(rst),
        .mem_read(mem_valid && mem_mem_read),
        .mem_write(mem_valid && mem_mem_write),
        .funct3(mem_funct3),
        .addr(mem_alu_result),
        .store_data_in(mem_rs2_data),
        .dmem_ready(dmem_ready),
        .dmem_rdata(dmem_rdata),
        .load_data(lsu_load_data),
        .load_valid(lsu_load_valid),
        .mem_stall(lsu_mem_stall),
        .misaligned_access(lsu_misaligned_access),
        .dmem_req(dmem_req),
        .dmem_we(dmem_we),
        .dmem_addr(dmem_addr),
        .dmem_wdata(dmem_wdata),
        .dmem_byte_en(dmem_byte_en)
    );

    assign mem_op_active = mem_valid && (mem_mem_read || mem_mem_write);
    assign mem_stage_complete = !mem_op_active || !lsu_mem_stall;

    mem_wb_reg u_mem_wb_reg (
        .clk(clk),
        .rst(rst),
        .stall(mem_wb_stall),
        .flush(mem_wb_flush),
        .alu_result_in(mem_alu_result),
        .mem_data_in(lsu_load_data),
        .rd_in(mem_rd),
        .reg_write_in(mem_reg_write && !lsu_misaligned_access),
        .mem_to_reg_in(mem_mem_to_reg && !lsu_misaligned_access),
        .valid_in(mem_valid && mem_stage_complete),
        .alu_result_out(wb_alu_result),
        .mem_data_out(wb_mem_data),
        .rd_out(wb_rd),
        .reg_write_out(wb_reg_write),
        .mem_to_reg_out(wb_mem_to_reg),
        .valid_out(wb_valid)
    );

    always_comb begin
        wb_sel = 2'b00;
        if (wb_mem_to_reg) begin
            wb_sel = 2'b01;
        end
    end

    wb_mux u_wb_mux (
        .alu_result(wb_alu_result),
        .mem_data(wb_mem_data),
        .pc_plus4(64'd0),
        .wb_sel(wb_sel),
        .wb_data(wb_data)
    );

    assign wb_write_enable = wb_valid && wb_reg_write && (wb_rd != 5'd0);

    pipeline_ctrl u_pipeline_ctrl (
        .ex_redirect_valid(ex_redirect_valid),
        .ex_redirect_pc(ex_branch_target_raw),
        .mem_stall(lsu_mem_stall),
        .if_stage_stall(if_stage_stall),
        .if_stage_flush(if_stage_flush),
        .if_id_stall(if_id_stall),
        .if_id_flush(if_id_flush),
        .id_ex_stall(id_ex_stall),
        .id_ex_flush(id_ex_flush),
        .ex_mem_stall(ex_mem_stall),
        .ex_mem_flush(ex_mem_flush),
        .mem_wb_stall(mem_wb_stall),
        .mem_wb_flush(mem_wb_flush),
        .redirect_valid(redirect_valid),
        .redirect_pc(redirect_pc)
    );

    assign dbg_if_pc = if_pc;
    assign dbg_wb_valid = wb_write_enable;
    assign dbg_wb_rd = wb_rd;
    assign dbg_wb_data = wb_data;
endmodule

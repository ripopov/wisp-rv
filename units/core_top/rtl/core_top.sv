/*
 * Module: core_top
 * Purpose: Integrate IF/ID/EX/MEM/WB pipeline stages into a Stage-09 RV64 core.
 * Interface: Clock/reset, instruction-memory and data-memory interfaces, plus debug writeback visibility.
 * Behavior: Single-issue in-order 5-stage pipeline with forwarding, load-use hazard stalling, machine-mode trap/CSR support, and RV64M operations.
 * Reset: Active-high synchronous reset for stage state elements.
 * Pipeline control: Handles branch/jump and trap redirects, load-use bubbles, divide busy stalls, and memory backpressure.
 * Corner cases: Trap/mret redirects override EX redirects; forwarding never sources x0.
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
    output logic [63:0] dbg_wb_data,
    output logic        dbg_retire_valid,
    output logic [63:0] dbg_retire_pc,
    output logic [31:0] dbg_retire_instr
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
    logic        load_use_stall;

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
    logic [11:0] id_system_imm;
    id_ctrl_t    id_ctrl_raw;
    id_ctrl_t    id_ctrl_masked;
    logic        id_issue_valid;
    logic        id_pipe_valid;
    logic [4:0]  id_rs1_addr;
    logic [4:0]  id_rs2_addr;
    logic [63:0] id_rs1_data;
    logic [63:0] id_rs2_data;
    logic        id_is_csr;
    logic [2:0]  id_csr_cmd;
    logic [11:0] id_csr_addr;
    logic [4:0]  id_csr_zimm;
    logic        id_csr_use_imm;
    logic        id_trap_illegal;
    logic        id_trap_ecall;
    logic        id_trap_ebreak;
    logic        id_is_mret;

    logic [63:0] ex_pc;
    logic [31:0] ex_instr;
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
    logic        ex_is_csr;
    logic [2:0]  ex_csr_cmd;
    logic [11:0] ex_csr_addr;
    logic [4:0]  ex_csr_zimm;
    logic        ex_csr_use_imm;
    logic        ex_trap_illegal;
    logic        ex_trap_ecall;
    logic        ex_trap_ebreak;
    logic        ex_is_mret;

    logic [63:0] ex_alu_result;
    logic        ex_branch_taken_raw;
    logic [63:0] ex_branch_target_raw;
    logic        ex_redirect_valid;
    logic [1:0]  forward_a_sel;
    logic [1:0]  forward_b_sel;
    logic [63:0] ex_rs1_data_fwd_live;
    logic [63:0] ex_rs2_data_fwd_live;
    logic [63:0] ex_rs1_data_fwd_hold;
    logic [63:0] ex_rs2_data_fwd_hold;
    logic [63:0] ex_hold_pc;
    logic        ex_hold_active;
    logic [63:0] ex_rs1_data_fwd;
    logic [63:0] ex_rs2_data_fwd;
    logic [63:0] ex_csr_wdata;
    logic        ex_is_mul;
    logic        ex_is_div;
    logic        ex_m_stall;
    logic        ex_m_flush;
    logic        ex_m_result_valid;
    logic [63:0] ex_m_result;
    logic [63:0] ex_result_final;
    logic        ex_valid_to_mem;
    logic        mul_op_valid;
    logic [63:0] mul_result;
    logic        div_op_valid;
    logic [63:0] div_result;

    logic [63:0] mem_pc;
    logic [31:0] mem_instr;
    logic [63:0] mem_alu_result;
    logic [63:0] mem_rs2_data;
    logic [63:0] mem_csr_wdata;
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
    logic        mem_is_csr;
    logic [2:0]  mem_csr_cmd;
    logic [11:0] mem_csr_addr;
    logic        mem_trap_illegal;
    logic        mem_trap_ecall;
    logic        mem_trap_ebreak;
    logic        mem_is_mret;

    logic [63:0] lsu_load_data;
    logic        lsu_load_valid;
    logic        lsu_mem_stall;
    logic        lsu_misaligned_access;
    logic        mem_op_active;
    logic        mem_stage_complete;

    logic [63:0] wb_pc;
    logic [31:0] wb_instr;
    logic [63:0] wb_alu_result;
    logic [63:0] wb_mem_data;
    logic [63:0] wb_csr_wdata;
    logic [4:0]  wb_rd;
    logic        wb_reg_write;
    logic        wb_mem_to_reg;
    logic        wb_valid;
    logic        wb_is_csr;
    logic [2:0]  wb_csr_cmd;
    logic [11:0] wb_csr_addr;
    logic        wb_trap_illegal;
    logic        wb_trap_ecall;
    logic        wb_trap_ebreak;
    logic        wb_is_mret;
    logic [1:0]  wb_sel;
    logic [63:0] wb_data_base;
    logic [63:0] wb_data;
    logic        wb_write_enable;
    logic        wb_allow_reg_write;
    logic        ex_mem_forward_reg_write;
    logic [63:0] ex_mem_forward_data;
    logic [63:0] wb_csr_rdata;
    logic        wb_csr_illegal;

    logic        retire_valid;
    logic        csr_commit_valid;
    logic [2:0]  csr_commit_cmd;
    logic [11:0] csr_commit_addr;
    logic [63:0] csr_commit_wdata;
    logic        trap_enter_valid;
    logic [63:0] trap_cause;
    logic [63:0] trap_tval;
    logic [63:0] trap_pc;
    logic        commit_mret_valid;

    logic [63:0] csr_mstatus;
    logic [63:0] csr_mie;
    logic [63:0] csr_mip;
    logic [63:0] csr_mtvec;
    logic [63:0] csr_mepc;

    logic        trap_redirect_valid;
    logic [63:0] trap_redirect_pc;
    logic        trap_update_valid;
    logic [63:0] trap_mepc;
    logic [63:0] trap_mcause;
    logic [63:0] trap_mtval;
    logic [63:0] trap_mstatus_new;
    logic        mret_update_valid;
    logic [63:0] mret_mstatus_new;

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
        id_pipe_valid = id_valid;
        id_system_imm = id_instr[31:20];

        id_is_csr = 1'b0;
        id_csr_cmd = CSR_CMD_NONE;
        id_csr_addr = id_instr[31:20];
        id_csr_zimm = id_rs1;
        id_csr_use_imm = 1'b0;
        id_trap_illegal = id_valid && id_illegal;
        id_trap_ecall = 1'b0;
        id_trap_ebreak = 1'b0;
        id_is_mret = 1'b0;

        id_ctrl_masked = '0;
        id_ctrl_masked.alu_op = ALU_OP_ADD;
        id_ctrl_masked.alu_src = ALU_SRC_REG;

        if (id_issue_valid) begin
            id_ctrl_masked = id_ctrl_raw;
        end

        if (id_issue_valid) begin
            if ((id_opcode == SYSTEM) &&
                ((id_funct3 == F3_CSRRW) ||
                 (id_funct3 == F3_CSRRS) ||
                 (id_funct3 == F3_CSRRC) ||
                 (id_funct3 == F3_CSRRWI) ||
                 (id_funct3 == F3_CSRRSI) ||
                 (id_funct3 == F3_CSRRCI))) begin
                id_is_csr = 1'b1;
                id_csr_addr = id_instr[31:20];
                id_csr_zimm = id_rs1;
                id_csr_use_imm = id_funct3[2];

                unique case (id_funct3)
                    F3_CSRRW: id_csr_cmd = CSR_CMD_RW;
                    F3_CSRRS: id_csr_cmd = CSR_CMD_RS;
                    F3_CSRRC: id_csr_cmd = CSR_CMD_RC;
                    F3_CSRRWI: id_csr_cmd = CSR_CMD_RWI;
                    F3_CSRRSI: id_csr_cmd = CSR_CMD_RSI;
                    F3_CSRRCI: id_csr_cmd = CSR_CMD_RCI;
                    default: id_csr_cmd = CSR_CMD_NONE;
                endcase

                if (id_csr_use_imm) begin
                    id_rs1_addr = 5'd0;
                end else begin
                    id_rs1_addr = id_rs1;
                end
                id_rs2_addr = 5'd0;
            end else begin
                id_rs1_addr = id_rs1;
                id_rs2_addr = id_rs2;
            end

            if ((id_opcode == SYSTEM) && (id_funct3 == F3_SYSTEM_PRIV)) begin
                id_trap_ecall = (id_system_imm == SYSTEM_IMM_ECALL);
                id_trap_ebreak = (id_system_imm == SYSTEM_IMM_EBREAK);
                id_is_mret = (id_system_imm == SYSTEM_IMM_MRET);
            end
        end else begin
            id_rs1_addr = 5'd0;
            id_rs2_addr = 5'd0;
        end
    end

    hazard_unit u_hazard_unit (
        .id_ex_valid(ex_valid),
        .id_ex_mem_read(ex_mem_read),
        .id_ex_is_csr(ex_is_csr),
        .id_ex_rd(ex_rd),
        .if_id_valid(id_issue_valid),
        .if_id_opcode(id_opcode),
        .if_id_funct3(id_funct3),
        .if_id_rs1(id_rs1),
        .if_id_rs2(id_rs2),
        .load_use_stall(load_use_stall)
    );

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
        .instr_in(id_instr),
        .rs1_data_in(id_rs1_data),
        .rs2_data_in(id_rs2_data),
        .imm_in(id_imm),
        .opcode_in(id_opcode),
        .rd_in(id_rd),
        .rs1_addr_in(id_rs1_addr),
        .rs2_addr_in(id_rs2_addr),
        .funct3_in(id_funct3),
        .funct7_in(id_funct7),
        .is_csr_in(id_is_csr),
        .csr_cmd_in(id_csr_cmd),
        .csr_addr_in(id_csr_addr),
        .csr_zimm_in(id_csr_zimm),
        .csr_use_imm_in(id_csr_use_imm),
        .trap_illegal_in(id_trap_illegal),
        .trap_ecall_in(id_trap_ecall),
        .trap_ebreak_in(id_trap_ebreak),
        .is_mret_in(id_is_mret),
        .alu_op_in(id_ctrl_masked.alu_op),
        .alu_src_in(id_ctrl_masked.alu_src),
        .mem_read_in(id_ctrl_masked.mem_read),
        .mem_write_in(id_ctrl_masked.mem_write),
        .reg_write_in(id_ctrl_masked.reg_write),
        .mem_to_reg_in(id_ctrl_masked.mem_to_reg),
        .branch_in(id_ctrl_masked.branch),
        .jump_in(id_ctrl_masked.jump),
        .is_word_op_in(id_ctrl_masked.is_word_op),
        .valid_in(id_pipe_valid),
        .pc_out(ex_pc),
        .instr_out(ex_instr),
        .rs1_data_out(ex_rs1_data),
        .rs2_data_out(ex_rs2_data),
        .imm_out(ex_imm),
        .opcode_out(ex_opcode),
        .rd_out(ex_rd),
        .rs1_addr_out(ex_rs1_addr),
        .rs2_addr_out(ex_rs2_addr),
        .funct3_out(ex_funct3),
        .funct7_out(ex_funct7),
        .is_csr_out(ex_is_csr),
        .csr_cmd_out(ex_csr_cmd),
        .csr_addr_out(ex_csr_addr),
        .csr_zimm_out(ex_csr_zimm),
        .csr_use_imm_out(ex_csr_use_imm),
        .trap_illegal_out(ex_trap_illegal),
        .trap_ecall_out(ex_trap_ecall),
        .trap_ebreak_out(ex_trap_ebreak),
        .is_mret_out(ex_is_mret),
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
        .rs1_data(ex_rs1_data_fwd),
        .rs2_data(ex_rs2_data_fwd),
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
    assign ex_m_flush = ex_redirect_valid || trap_redirect_valid;

    mul_unit u_mul_unit (
        .opcode(ex_opcode),
        .funct3(ex_funct3),
        .funct7(ex_funct7),
        .rs1_data(ex_rs1_data_fwd),
        .rs2_data(ex_rs2_data_fwd),
        .op_valid(mul_op_valid),
        .result(mul_result)
    );

    div_unit u_div_unit (
        .opcode(ex_opcode),
        .funct3(ex_funct3),
        .funct7(ex_funct7),
        .rs1_data(ex_rs1_data_fwd),
        .rs2_data(ex_rs2_data_fwd),
        .op_valid(div_op_valid),
        .result(div_result)
    );

    assign ex_is_mul = ex_valid && mul_op_valid;
    assign ex_is_div = ex_valid && div_op_valid;

    m_ext_ctrl u_m_ext_ctrl (
        .clk(clk),
        .rst(rst),
        .flush(ex_m_flush),
        .ex_valid(ex_valid),
        .ex_is_mul(ex_is_mul),
        .ex_is_div(ex_is_div),
        .mul_result(mul_result),
        .div_result(div_result),
        .ex_busy_stall(ex_m_stall),
        .m_result_valid(ex_m_result_valid),
        .m_result(ex_m_result)
    );

    always_comb begin
        ex_result_final = ex_alu_result;
        ex_valid_to_mem = ex_valid;

        if (ex_is_mul || ex_is_div) begin
            ex_result_final = ex_m_result;
        end

        if (ex_is_div) begin
            ex_valid_to_mem = ex_m_result_valid;
        end
    end

    ex_mem_reg u_ex_mem_reg (
        .clk(clk),
        .rst(rst),
        .stall(ex_mem_stall),
        .flush(ex_mem_flush),
        .pc_in(ex_pc),
        .instr_in(ex_instr),
        .alu_result_in(ex_result_final),
        .rs2_data_in(ex_rs2_data_fwd),
        .csr_wdata_in(ex_csr_wdata),
        .rd_in(ex_rd),
        .funct3_in(ex_funct3),
        .is_csr_in(ex_is_csr),
        .csr_cmd_in(ex_csr_cmd),
        .csr_addr_in(ex_csr_addr),
        .trap_illegal_in(ex_trap_illegal),
        .trap_ecall_in(ex_trap_ecall),
        .trap_ebreak_in(ex_trap_ebreak),
        .is_mret_in(ex_is_mret),
        .mem_read_in(ex_mem_read),
        .mem_write_in(ex_mem_write),
        .reg_write_in(ex_reg_write),
        .mem_to_reg_in(ex_mem_to_reg),
        .is_word_op_in(ex_is_word_op),
        .branch_taken_in(ex_redirect_valid),
        .branch_target_in(ex_branch_target_raw),
        .valid_in(ex_valid_to_mem),
        .pc_out(mem_pc),
        .instr_out(mem_instr),
        .alu_result_out(mem_alu_result),
        .rs2_data_out(mem_rs2_data),
        .csr_wdata_out(mem_csr_wdata),
        .rd_out(mem_rd),
        .funct3_out(mem_funct3),
        .is_csr_out(mem_is_csr),
        .csr_cmd_out(mem_csr_cmd),
        .csr_addr_out(mem_csr_addr),
        .trap_illegal_out(mem_trap_illegal),
        .trap_ecall_out(mem_trap_ecall),
        .trap_ebreak_out(mem_trap_ebreak),
        .is_mret_out(mem_is_mret),
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
        .pc_in(mem_pc),
        .instr_in(mem_instr),
        .alu_result_in(mem_alu_result),
        .mem_data_in(lsu_load_data),
        .csr_wdata_in(mem_csr_wdata),
        .rd_in(mem_rd),
        .is_csr_in(mem_is_csr),
        .csr_cmd_in(mem_csr_cmd),
        .csr_addr_in(mem_csr_addr),
        .trap_illegal_in(mem_trap_illegal),
        .trap_ecall_in(mem_trap_ecall),
        .trap_ebreak_in(mem_trap_ebreak),
        .is_mret_in(mem_is_mret),
        .reg_write_in(mem_reg_write && !lsu_misaligned_access),
        .mem_to_reg_in(mem_mem_to_reg && !lsu_misaligned_access),
        .valid_in(mem_valid && mem_stage_complete),
        .pc_out(wb_pc),
        .instr_out(wb_instr),
        .alu_result_out(wb_alu_result),
        .mem_data_out(wb_mem_data),
        .csr_wdata_out(wb_csr_wdata),
        .rd_out(wb_rd),
        .is_csr_out(wb_is_csr),
        .csr_cmd_out(wb_csr_cmd),
        .csr_addr_out(wb_csr_addr),
        .trap_illegal_out(wb_trap_illegal),
        .trap_ecall_out(wb_trap_ecall),
        .trap_ebreak_out(wb_trap_ebreak),
        .is_mret_out(wb_is_mret),
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
        .wb_data(wb_data_base)
    );

    assign ex_mem_forward_reg_write = mem_valid &&
                                      mem_reg_write &&
                                      !mem_mem_to_reg &&
                                      !mem_is_csr;
    assign ex_mem_forward_data = mem_alu_result;

    forwarding_unit u_forwarding_unit (
        .ex_mem_reg_write(ex_mem_forward_reg_write),
        .ex_mem_rd(mem_rd),
        .mem_wb_reg_write(wb_allow_reg_write),
        .mem_wb_rd(wb_rd),
        .id_ex_rs1(ex_rs1_addr),
        .id_ex_rs2(ex_rs2_addr),
        .forward_a_sel(forward_a_sel),
        .forward_b_sel(forward_b_sel)
    );

    always_comb begin
        ex_rs1_data_fwd_live = ex_rs1_data;
        ex_rs2_data_fwd_live = ex_rs2_data;

        unique case (forward_a_sel)
            2'b01: ex_rs1_data_fwd_live = ex_mem_forward_data;
            2'b10: ex_rs1_data_fwd_live = wb_data;
            default: ex_rs1_data_fwd_live = ex_rs1_data;
        endcase

        unique case (forward_b_sel)
            2'b01: ex_rs2_data_fwd_live = ex_mem_forward_data;
            2'b10: ex_rs2_data_fwd_live = wb_data;
            default: ex_rs2_data_fwd_live = ex_rs2_data;
        endcase

        ex_rs1_data_fwd = ex_rs1_data_fwd_live;
        ex_rs2_data_fwd = ex_rs2_data_fwd_live;

        if (ex_hold_active && (ex_pc == ex_hold_pc)) begin
            ex_rs1_data_fwd = ex_rs1_data_fwd_hold;
            ex_rs2_data_fwd = ex_rs2_data_fwd_hold;
        end

        if (ex_csr_use_imm) begin
            ex_csr_wdata = {59'd0, ex_csr_zimm};
        end else begin
            ex_csr_wdata = ex_rs1_data_fwd;
        end
    end

    always_ff @(posedge clk) begin
        if (rst || id_ex_flush) begin
            ex_rs1_data_fwd_hold <= 64'd0;
            ex_rs2_data_fwd_hold <= 64'd0;
            ex_hold_pc <= 64'd0;
            ex_hold_active <= 1'b0;
        end else begin
            if (lsu_mem_stall) begin
                ex_rs1_data_fwd_hold <= ex_rs1_data_fwd;
                ex_rs2_data_fwd_hold <= ex_rs2_data_fwd;
                ex_hold_pc <= ex_pc;
                ex_hold_active <= 1'b1;
            end else begin
                if (ex_hold_active && (ex_pc != ex_hold_pc)) begin
                    ex_hold_active <= 1'b0;
                end

                if (!(ex_hold_active && (ex_pc == ex_hold_pc))) begin
                    ex_rs1_data_fwd_hold <= ex_rs1_data_fwd_live;
                    ex_rs2_data_fwd_hold <= ex_rs2_data_fwd_live;
                end
            end
        end
    end

    csr_file u_csr_file (
        .clk(clk),
        .rst(rst),
        .csr_req_valid(wb_valid && wb_is_csr),
        .csr_req_addr(wb_csr_addr),
        .csr_req_cmd(wb_csr_cmd),
        .csr_req_wdata(wb_csr_wdata),
        .csr_req_rdata(wb_csr_rdata),
        .csr_req_illegal(wb_csr_illegal),
        .csr_commit_valid(csr_commit_valid),
        .csr_commit_addr(csr_commit_addr),
        .csr_commit_cmd(csr_commit_cmd),
        .csr_commit_wdata(csr_commit_wdata),
        .trap_update_valid(trap_update_valid),
        .trap_mepc(trap_mepc),
        .trap_mcause(trap_mcause),
        .trap_mtval(trap_mtval),
        .trap_mstatus_new(trap_mstatus_new),
        .mret_update_valid(mret_update_valid),
        .mret_mstatus_new(mret_mstatus_new),
        .inc_minstret(retire_valid),
        .csr_mstatus(csr_mstatus),
        .csr_mie(csr_mie),
        .csr_mip(csr_mip),
        .csr_mtvec(csr_mtvec),
        .csr_mepc(csr_mepc)
    );

    commit_ctrl u_commit_ctrl (
        .wb_valid(wb_valid),
        .wb_pc(wb_pc),
        .wb_instr(wb_instr),
        .wb_reg_write(wb_reg_write),
        .wb_is_csr(wb_is_csr),
        .wb_csr_cmd(wb_csr_cmd),
        .wb_csr_addr(wb_csr_addr),
        .wb_csr_wdata(wb_csr_wdata),
        .wb_trap_illegal(wb_trap_illegal),
        .wb_trap_ecall(wb_trap_ecall),
        .wb_trap_ebreak(wb_trap_ebreak),
        .wb_is_mret(wb_is_mret),
        .csr_access_illegal(wb_csr_illegal),
        .wb_allow_reg_write(wb_allow_reg_write),
        .retire_valid(retire_valid),
        .csr_commit_valid(csr_commit_valid),
        .csr_commit_cmd(csr_commit_cmd),
        .csr_commit_addr(csr_commit_addr),
        .csr_commit_wdata(csr_commit_wdata),
        .trap_enter_valid(trap_enter_valid),
        .trap_cause(trap_cause),
        .trap_tval(trap_tval),
        .trap_pc(trap_pc),
        .mret_valid(commit_mret_valid)
    );

    trap_ctrl u_trap_ctrl (
        .trap_enter_valid(trap_enter_valid),
        .trap_cause(trap_cause),
        .trap_tval(trap_tval),
        .trap_pc(trap_pc),
        .mret_valid(commit_mret_valid),
        .csr_mstatus(csr_mstatus),
        .csr_mtvec(csr_mtvec),
        .csr_mepc(csr_mepc),
        .redirect_valid(trap_redirect_valid),
        .redirect_pc(trap_redirect_pc),
        .trap_update_valid(trap_update_valid),
        .trap_mepc(trap_mepc),
        .trap_mcause(trap_mcause),
        .trap_mtval(trap_mtval),
        .trap_mstatus_new(trap_mstatus_new),
        .mret_update_valid(mret_update_valid),
        .mret_mstatus_new(mret_mstatus_new)
    );

    assign wb_data = wb_is_csr ? wb_csr_rdata : wb_data_base;
    assign wb_write_enable = wb_allow_reg_write && (wb_rd != 5'd0);

    pipeline_ctrl u_pipeline_ctrl (
        .ex_redirect_valid(ex_redirect_valid),
        .ex_redirect_pc(ex_branch_target_raw),
        .wb_redirect_valid(trap_redirect_valid),
        .wb_redirect_pc(trap_redirect_pc),
        .mem_stall(lsu_mem_stall),
        .ex_busy_stall(ex_m_stall),
        .load_use_stall(load_use_stall),
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
    assign dbg_retire_valid = retire_valid;
    assign dbg_retire_pc = wb_pc;
    assign dbg_retire_instr = wb_instr;
endmodule

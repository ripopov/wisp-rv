/*
 * Package: rv64_pkg
 * Purpose: Shared RV64I decode constants and control/data types.
 * Interface: Imported by decode and control modules.
 * Behavior: Provides compile-time constants, enums, and packed structs.
 * Reset: Not applicable (package only).
 * Pipeline control: Provides common types used by pipeline stages.
 * Corner cases: OP-IMM shift validation must treat instr[25] as shamt[5].
 */
package rv64_pkg;
    // Opcode fields (instr[6:0]).
    localparam logic [6:0] OP         = 7'b0110011;
    localparam logic [6:0] OP_IMM     = 7'b0010011;
    localparam logic [6:0] OP_32      = 7'b0111011;
    localparam logic [6:0] OP_IMM_32  = 7'b0011011;
    localparam logic [6:0] LOAD       = 7'b0000011;
    localparam logic [6:0] STORE      = 7'b0100011;
    localparam logic [6:0] BRANCH     = 7'b1100011;
    localparam logic [6:0] LUI        = 7'b0110111;
    localparam logic [6:0] AUIPC      = 7'b0010111;
    localparam logic [6:0] JAL        = 7'b1101111;
    localparam logic [6:0] JALR       = 7'b1100111;
    localparam logic [6:0] SYSTEM     = 7'b1110011;
    localparam logic [6:0] FENCE      = 7'b0001111;

    // OP / OP-IMM funct3 fields.
    localparam logic [2:0] F3_ADD_SUB = 3'b000;
    localparam logic [2:0] F3_SLL     = 3'b001;
    localparam logic [2:0] F3_SLT     = 3'b010;
    localparam logic [2:0] F3_SLTU    = 3'b011;
    localparam logic [2:0] F3_XOR     = 3'b100;
    localparam logic [2:0] F3_SRL_SRA = 3'b101;
    localparam logic [2:0] F3_OR      = 3'b110;
    localparam logic [2:0] F3_AND     = 3'b111;

    // Load funct3 fields.
    localparam logic [2:0] F3_LB      = 3'b000;
    localparam logic [2:0] F3_LH      = 3'b001;
    localparam logic [2:0] F3_LW      = 3'b010;
    localparam logic [2:0] F3_LD      = 3'b011;
    localparam logic [2:0] F3_LBU     = 3'b100;
    localparam logic [2:0] F3_LHU     = 3'b101;
    localparam logic [2:0] F3_LWU     = 3'b110;

    // Store funct3 fields.
    localparam logic [2:0] F3_SB      = 3'b000;
    localparam logic [2:0] F3_SH      = 3'b001;
    localparam logic [2:0] F3_SW      = 3'b010;
    localparam logic [2:0] F3_SD      = 3'b011;

    // Branch funct3 fields.
    localparam logic [2:0] F3_BEQ     = 3'b000;
    localparam logic [2:0] F3_BNE     = 3'b001;
    localparam logic [2:0] F3_BLT     = 3'b100;
    localparam logic [2:0] F3_BGE     = 3'b101;
    localparam logic [2:0] F3_BLTU    = 3'b110;
    localparam logic [2:0] F3_BGEU    = 3'b111;

    // SYSTEM/FENCE funct3 fields and immediate values.
    localparam logic [2:0] F3_SYSTEM_PRIV = 3'b000;
    localparam logic [2:0] F3_FENCE       = 3'b000;
    localparam logic [11:0] SYSTEM_IMM_ECALL  = 12'h000;
    localparam logic [11:0] SYSTEM_IMM_EBREAK = 12'h001;

    // ALU operation encoding, matched to units/alu/rtl/alu.sv op mapping.
    typedef enum logic [3:0] {
        ALU_OP_ADD  = 4'h0,
        ALU_OP_SUB  = 4'h1,
        ALU_OP_AND  = 4'h2,
        ALU_OP_OR   = 4'h3,
        ALU_OP_XOR  = 4'h4,
        ALU_OP_SLT  = 4'h5,
        ALU_OP_SLTU = 4'h6,
        ALU_OP_SLL  = 4'h7,
        ALU_OP_SRL  = 4'h8,
        ALU_OP_SRA  = 4'h9
    } alu_op_t;

    typedef enum logic [2:0] {
        R_TYPE = 3'd0,
        I_TYPE = 3'd1,
        S_TYPE = 3'd2,
        B_TYPE = 3'd3,
        U_TYPE = 3'd4,
        J_TYPE = 3'd5
    } instr_format_t;

    typedef enum logic {
        ALU_SRC_REG = 1'b0,
        ALU_SRC_IMM = 1'b1
    } alu_src_t;

    typedef struct packed {
        alu_op_t   alu_op;
        alu_src_t  alu_src;
        logic      mem_read;
        logic      mem_write;
        logic      reg_write;
        logic      mem_to_reg;
        logic      branch;
        logic      jump;
        logic      is_word_op;
    } id_ctrl_t;

    // Pipeline register payloads used starting in Stage 02.
    typedef struct packed {
        logic [63:0] pc;
        logic [31:0] instr;
        logic        valid;
    } if_id_reg_t;

    typedef struct packed {
        logic [63:0] pc;
        logic [63:0] rs1_data;
        logic [63:0] rs2_data;
        logic [63:0] imm;
        logic [6:0]  opcode;
        logic [4:0]  rd;
        logic [4:0]  rs1_addr;
        logic [4:0]  rs2_addr;
        logic [2:0]  funct3;
        logic [6:0]  funct7;
        id_ctrl_t    ctrl;
        logic        valid;
    } id_ex_reg_t;

    typedef struct packed {
        logic mem_read;
        logic mem_write;
        logic reg_write;
        logic mem_to_reg;
        logic is_word_op;
    } ex_mem_ctrl_t;

    typedef struct packed {
        logic [63:0]   pc;
        logic [63:0]   alu_result;
        logic [63:0]   rs2_data;
        logic [4:0]    rd;
        logic [2:0]    funct3;
        ex_mem_ctrl_t  ctrl;
        logic          branch_taken;
        logic [63:0]   branch_target;
        logic          valid;
    } ex_mem_reg_t;

    typedef struct packed {
        logic reg_write;
        logic mem_to_reg;
    } mem_wb_ctrl_t;

    typedef struct packed {
        logic [63:0]   alu_result;
        logic [63:0]   mem_data;
        logic [4:0]    rd;
        mem_wb_ctrl_t  ctrl;
        logic          valid;
    } mem_wb_reg_t;
endpackage

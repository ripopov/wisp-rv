import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def test_package_constants(dut):
    await Timer(1, unit="ns")

    assert int(dut.opcode_op.value) == 0b0110011
    assert int(dut.opcode_op_imm.value) == 0b0010011
    assert int(dut.opcode_op_32.value) == 0b0111011
    assert int(dut.opcode_op_imm_32.value) == 0b0011011
    assert int(dut.opcode_load.value) == 0b0000011
    assert int(dut.opcode_store.value) == 0b0100011

    assert int(dut.alu_add.value) == 0x0
    assert int(dut.alu_sra.value) == 0x9

    assert int(dut.fmt_i.value) == 1
    assert int(dut.fmt_j.value) == 5

    assert int(dut.bits_if_id.value) == 97
    assert int(dut.bits_id_ex.value) == 359
    assert int(dut.bits_ex_mem.value) == 387
    assert int(dut.bits_mem_wb.value) == 316

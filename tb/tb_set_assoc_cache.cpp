#include <cstdint>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

#include <systemc>

#include "Vset_assoc_cache_2way.h"

namespace {

struct Resp {
    bool hit;
    uint32_t data;
};

std::string hex32(uint32_t value) {
    std::ostringstream oss;
    oss << "0x" << std::hex << std::setw(8) << std::setfill('0') << value;
    return oss.str();
}

}  // namespace

int sc_main(int argc, char** argv) {
    (void)argc;
    (void)argv;

    sc_core::sc_signal<bool> clk("clk");
    sc_core::sc_signal<bool> rst_n("rst_n");

    sc_core::sc_signal<bool> req_valid("req_valid");
    sc_core::sc_signal<bool> req_ready("req_ready");
    sc_core::sc_signal<bool> req_write("req_write");
    sc_core::sc_signal<uint32_t> req_addr("req_addr");
    sc_core::sc_signal<uint32_t> req_wdata("req_wdata");
    sc_core::sc_signal<uint32_t> req_wmask("req_wmask");

    sc_core::sc_signal<bool> resp_valid("resp_valid");
    sc_core::sc_signal<bool> resp_hit("resp_hit");
    sc_core::sc_signal<uint32_t> resp_rdata("resp_rdata");

    Vset_assoc_cache_2way dut("dut");
    dut.clk(clk);
    dut.rst_n(rst_n);
    dut.req_valid(req_valid);
    dut.req_ready(req_ready);
    dut.req_write(req_write);
    dut.req_addr(req_addr);
    dut.req_wdata(req_wdata);
    dut.req_wmask(req_wmask);
    dut.resp_valid(resp_valid);
    dut.resp_hit(resp_hit);
    dut.resp_rdata(resp_rdata);

    auto advance_cycle = [&]() {
        clk.write(true);
        sc_core::sc_start(5, sc_core::SC_NS);
        clk.write(false);
        sc_core::sc_start(5, sc_core::SC_NS);
    };

    auto clear_req = [&]() {
        req_valid.write(false);
        req_write.write(false);
        req_addr.write(0U);
        req_wdata.write(0U);
        req_wmask.write(0U);
    };

    auto expect = [&](bool condition, const std::string& message) {
        if (!condition) {
            throw std::runtime_error(message);
        }
    };

    auto wait_for_req_ready = [&]() {
        constexpr int MAX_WAIT_CYCLES = 200;
        for (int i = 0; i < MAX_WAIT_CYCLES; ++i) {
            if (req_ready.read()) {
                return;
            }
            advance_cycle();
        }
        throw std::runtime_error("Timed out waiting for req_ready");
    };

    auto send_req = [&](bool is_write, uint32_t addr, uint32_t wdata, uint32_t wmask) {
        wait_for_req_ready();

        req_valid.write(true);
        req_write.write(is_write);
        req_addr.write(addr);
        req_wdata.write(wdata);
        req_wmask.write(wmask & 0xFU);

        advance_cycle();
        clear_req();
    };

    auto wait_resp = [&]() -> Resp {
        constexpr int MAX_WAIT_CYCLES = 200;
        for (int i = 0; i < MAX_WAIT_CYCLES; ++i) {
            if (resp_valid.read()) {
                return Resp{resp_hit.read(), resp_rdata.read()};
            }
            advance_cycle();
        }
        throw std::runtime_error("Timed out waiting for resp_valid");
    };

    try {
        clk.write(false);
        rst_n.write(false);
        clear_req();
        sc_core::sc_start(sc_core::SC_ZERO_TIME);

        for (int i = 0; i < 4; ++i) {
            advance_cycle();
        }

        rst_n.write(true);

        Resp resp = {};

        send_req(false, 0x00000010U, 0x00000000U, 0x0U);
        resp = wait_resp();
        expect(!resp.hit, "Expected read miss for empty cache");

        send_req(true, 0x00000010U, 0xDEADBEEFU, 0xFU);
        resp = wait_resp();
        expect(!resp.hit, "Expected write miss and allocation");

        send_req(false, 0x00000010U, 0x00000000U, 0x0U);
        resp = wait_resp();
        expect(resp.hit && resp.data == 0xDEADBEEFU,
               "Expected read hit with DEADBEEF, got hit=" + std::to_string(resp.hit) +
                   " data=" + hex32(resp.data));

        send_req(true, 0x00000010U, 0x0000AAAAU, 0x3U);
        resp = wait_resp();
        expect(resp.hit, "Expected write hit for existing line");

        send_req(false, 0x00000010U, 0x00000000U, 0x0U);
        resp = wait_resp();
        expect(resp.hit && resp.data == 0xDEADAAAAU,
               "Expected masked write update to DEADAAAA, got " + hex32(resp.data));

        send_req(true, 0x00000110U, 0x12345678U, 0xFU);
        resp = wait_resp();
        expect(!resp.hit, "Expected second tag in same set to allocate in other way");

        send_req(false, 0x00000010U, 0x00000000U, 0x0U);
        resp = wait_resp();
        expect(resp.hit && resp.data == 0xDEADAAAAU,
               "Expected first line to remain present after 2-way fill");

        send_req(false, 0x00000110U, 0x00000000U, 0x0U);
        resp = wait_resp();
        expect(resp.hit && resp.data == 0x12345678U,
               "Expected second line hit with 12345678");

        std::cout << "PASS: set_assoc_cache_2way SystemC + Verilator test" << std::endl;
        for (int i = 0; i < 4; ++i) {
            advance_cycle();
        }
    } catch (const std::exception& ex) {
        std::cerr << "FAIL: " << ex.what() << std::endl;
        dut.final();
        return 1;
    }

    dut.final();
    return 0;
}

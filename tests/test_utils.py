import pytest

from latency_monitor.utils import parse_mtr, parse_dig


class TestParseMtr:
    def test_parse_mtr_valid_output(self):
        output = """Start: 2024-01-10T12:00:00+0000
HOST: server                      Loss%   Snt   Last   Avg  Best  Wrst StDev
  1.|-- 192.168.1.1               0.0%    10    1.2   1.5   1.0   2.0   0.3
  2.|-- 10.0.0.1                  0.0%    10    5.0   5.5   4.5   6.0   0.5
  3.|-- 8.8.8.8                   0.0%    10   10.5  11.2   9.8  15.3   1.5"""

        result = parse_mtr(output, "8.8.8.8")

        assert result["loss"] == 0.0
        assert result["snt"] == 10
        assert result["last"] == 10.5
        assert result["avg"] == 11.2
        assert result["best"] == 9.8
        assert result["worst"] == 15.3
        assert result["stdev"] == 1.5

    def test_parse_mtr_with_packet_loss(self):
        output = """Start: 2024-01-10T12:00:00+0000
HOST: server                      Loss%   Snt   Last   Avg  Best  Wrst StDev
  1.|-- 8.8.8.8                  25.5%    10   10.5  11.2   9.8  15.3   1.5"""

        result = parse_mtr(output, "8.8.8.8")

        assert result["loss"] == 25.5
        assert result["snt"] == 10

    def test_parse_mtr_ipv6_target(self):
        output = """Start: 2024-01-10T12:00:00+0000
HOST: server                      Loss%   Snt   Last   Avg  Best  Wrst StDev
  1.|-- 2001:4860:4860::8888      0.0%    10   15.2  16.0  14.5  18.0   1.2"""

        result = parse_mtr(output, "2001:4860:4860::8888")

        assert result["loss"] == 0.0
        assert result["avg"] == 16.0

    def test_parse_mtr_target_not_found(self):
        output = """Start: 2024-01-10T12:00:00+0000
HOST: server                      Loss%   Snt   Last   Avg  Best  Wrst StDev
  1.|-- 192.168.1.1               0.0%    10    1.2   1.5   1.0   2.0   0.3"""

        with pytest.raises(ValueError, match="Target IP 8.8.8.8 not found in MTR output"):
            parse_mtr(output, "8.8.8.8")

    def test_parse_mtr_empty_output(self):
        with pytest.raises(ValueError, match="Target IP 8.8.8.8 not found in MTR output"):
            parse_mtr("", "8.8.8.8")


class TestParseDig:
    def test_parse_dig_valid_output(self):
        output = """; <<>> DiG 9.18.18-0ubuntu0.22.04.1-Ubuntu <<>> google.com @8.8.8.8
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 12345
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; QUESTION SECTION:
;google.com.                    IN      A

;; ANSWER SECTION:
google.com.             300     IN      A       142.250.80.46

;; Query time: 42 msec
;; SERVER: 8.8.8.8#53(8.8.8.8) (UDP)
;; WHEN: Wed Jan 10 12:00:00 UTC 2024
;; MSG SIZE  rcvd: 55"""

        result = parse_dig(output)

        assert result == 42

    def test_parse_dig_zero_query_time(self):
        output = """;; Query time: 0 msec
;; SERVER: 1.1.1.1#53(1.1.1.1) (UDP)"""

        result = parse_dig(output)

        assert result == 0

    def test_parse_dig_large_query_time(self):
        output = """;; Query time: 1234 msec
;; SERVER: 1.1.1.1#53(1.1.1.1) (UDP)"""

        result = parse_dig(output)

        assert result == 1234

    def test_parse_dig_missing_query_time(self):
        output = """; <<>> DiG 9.18.18-0ubuntu0.22.04.1-Ubuntu <<>> google.com @8.8.8.8
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 12345"""

        with pytest.raises(ValueError, match="Query time not found in dig output"):
            parse_dig(output)

    def test_parse_dig_empty_output(self):
        with pytest.raises(ValueError, match="Query time not found in dig output"):
            parse_dig("")

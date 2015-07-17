# Copyright 2014 ETH Zurich
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
:mod:`lib_packet_ext_traceroute_test` --- lib.packet.ext.traceroute unit tests
==============================================================================
"""
# Stdlib
from unittest.mock import patch, MagicMock

# External packages
import nose
import nose.tools as ntools

# SCION
from lib.packet.ext.traceroute import TracerouteExt, traceroute_ext_handler


class TestTracerouteExtInit(object):
    """
    Unit tests for lib.packet.ext.traceroute.TracerouteExt.__init__
    """
    @patch("lib.packet.ext.traceroute.ExtensionHeader.__init__", autospec=True)
    def test_basic(self, ext_hdr_init):
        ext = TracerouteExt()
        ntools.eq_(ext.hops, [])
        ext_hdr_init.assert_called_once_with(ext)

    @patch("lib.packet.ext.traceroute.TracerouteExt.parse_payload",
           autospec=True)
    @patch("lib.packet.ext.traceroute.ExtensionHeader.parse", autospec=True)
    def test_raw(self, parse, parse_payload):
        ext = TracerouteExt('data')
        parse.assert_called_once_with(ext, 'data')
        parse_payload.assert_called_once_with(ext)


class TestTracerouteExtParsePayload(object):
    """
    Unit tests for lib.packet.ext.traceroute.TracerouteExt.parse_payload
    """
    @patch("lib.packet.ext.traceroute.ISD_AD.from_raw", spec_set=[],
           new_callable=MagicMock)
    def test(self, isd_ad):
        ext = TracerouteExt()
        ext.hops = [1]
        ext.payload = b'\x00' * 6 + bytes.fromhex('0102 0304 0506 0708') * 2
        isd_ad.side_effect = [(1, 2), (3, 4)]
        ext.parse_payload()
        ntools.eq_(ext.hops, [1, (1, 2, 0x0506, 0x0708),
                              (3, 4, 0x0506, 0x0708)])


class TestTracerouteExtAppendHop(object):
    """
    Unit tests for lib.packet.ext.traceroute.TracerouteExt.append_hop
    """
    def test(self):
        ext = TracerouteExt()
        ext.hops = [1]
        ext._hdr_len = 2
        ext.append_hop(3, 4, 5, 6)
        ntools.eq_(ext.hops, [1, (3, 4, 5, 6)])
        ntools.eq_(ext._hdr_len, 3)


class TestTracerouteExtPack(object):
    """
    Unit tests for lib.packet.ext.traceroute.TracerouteExt.pack
    """
    @patch("lib.packet.ext.traceroute.ExtensionHeader.pack", autospec=True)
    @patch("lib.packet.ext.traceroute.ISD_AD", autospec=True)
    def test(self, isd_ad, ext_hdr_pack):
        isd_ad_mock = isd_ad.return_value = MagicMock(spec_set=['pack'])
        isd_ad_mock.pack.side_effect = [b'isd_ad1', b'isd_ad2']
        ext = TracerouteExt()
        ext.hops = [(1, 2, 3, 4), (5, 6, 7, 8)]
        payload = b'\x00' * 6 + b'isd_ad1' + bytes.fromhex('0003 0004') \
                  + b'isd_ad2' + bytes.fromhex('0007 0008')
        ntools.eq_(ext.pack(), ext_hdr_pack.return_value)
        isd_ad.assert_any_call(1, 2)
        isd_ad.assert_any_call(5, 6)
        ntools.eq_(isd_ad_mock.pack.call_count, 2)
        ntools.eq_(ext.payload, payload)
        ext_hdr_pack.assert_called_once_with(ext)


class TestTracerouteExtHandler(object):
    """
    Unit tests for lib.packet.ext.traceroute.traceroute_ext_handler
    """
    @patch("lib.packet.ext.traceroute.time.time", autospec=True)
    def test(self, time):
        time.return_value = 123
        ext = MagicMock(spec_set=['append_hop'])
        topo = MagicMock(spec_set=['isd_id', 'ad_id'])
        iface = MagicMock(spec_set=['if_id'])
        ts = (123 * 1000) % 2**16
        traceroute_ext_handler(ext=ext, topo=topo, iface=iface)
        ext.append_hop.assert_called_once_with(topo.isd_id, topo.ad_id,
                                               iface.if_id, ts)


if __name__ == "__main__":
    nose.run(defaultTest=__name__)
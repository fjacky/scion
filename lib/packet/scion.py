"""
scion.py

Copyright 2014 ETH Zurich

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import logging

from bitstring import BitArray
import bitstring

from lib.packet.ext_hdr import ExtensionHeader, ICNExtHdr
from lib.packet.host_addr import (AddressLengths, IPv4HostAddr,
                                  IPv6HostAddr, SCIONHostAddr, HostAddr)
from lib.packet.opaque_field import InfoOpaqueField, OpaqueField
from lib.packet.packet_base import HeaderBase, PacketBase
from lib.packet.path import PathType, CorePath, PeerPath, CrossOverPath, \
    EmptyPath


class PacketType(object):
    """
    Defines constants for the SCION packet types.
    """
    DATA = 0  # data packet
    AID_REQ = 1  # Address request to local elements (from SCIONSwitch)
    AID_REP = 2  # AID reply to switch
    TO_LOCAL_ADDR = 100  # Threshold to distinguish local control packets
    BEACON = 101  # PCB type
    CERT_REQ_LOCAL = 102  # local certificate request (to certificate server)
    CERT_REP_LOCAL = 103  # local certificate reply (from certificate server)
    CERT_REQ = 104  # Certificate Request to parent AD
    CERT_REP = 105  # Certificate Reply from parent AD
    PATH_REQ_LOCAL = 106  # path request to local path server
    PATH_REP_LOCAL = 107  # path reply from local path server
    PATH_REQ = 108  # Path request to TDC
    PATH_REP = 109  # Path reply from TDC
    PATH_REG = 110  # Path registration to TDC
    UP_PATH = 111  # up-path to TDC (beacon server -> path server)
    ROT_REQ_LOCAL = 112  # ROT file reply to local certificate server
    ROT_REP_LOCAL = 113  # ROT file reply from local certificate server
    OFG_KEY_REQ = 114  # opaque field generation key request to CS
    OFG_KEY_REP = 115  # opaque field generation key reply from CS
    IFID_REQ = 116  # IF ID request to the peer router (of the neighbor AD)
    IFID_REP = 117  # IF ID reply from the peer router
    ROT_REQ = 118  # Root of Trust file request to parent AD
    ROT_REP = 119  # Root of Trust file reply from parent AD
    PATH_REQ_TDC = 120  # Request for a path to other TDC
    PATH_REP_TDC = 121  # Reply from other TDC


class SignatureType(object):
    """
    Defines constants for the possible sizes of signatures.
    """
    SIZE_128 = 0
    SIZE_256 = 1
    SIZE_384 = 2


class IDSize(object):
    """
    Defines constants for the lengths of AIDs and TIDs.
    """
    SIZE_TID = 4
    SIZE_AID = 8





class SCIONCommonHdr(HeaderBase):
    """
    Encapsulates the common header for SCION packets.
    """

    LEN = 8

    def __init__(self, raw=None):
        HeaderBase.__init__(self)
        self.type = PacketType.DATA  # Type of the packet.
        self.src_addr_len = 0  # Length of the src address.
        self.dst_addr_len = 0  # Length of the dst address.
        self.total_len = 0  # Total length of the packet.
        self.timestamp = 0  # Offset inside the packet to the timestamp.
        self.current_of = 0  # Index of the current opaque field.
        self.next_hdr = 0  # Type of the next hdr field (IP protocol numbers).
        self.hdr_len = 0  # Header length including the path.

        if raw is not None:
            self.parse(raw)

    @classmethod
    def from_values(cls, pkt_type, src_addr_len, dst_addr_len, next_hdr):
        """
        Returns a SCIONCommonHdr with the values specified.
        """
        chdr = SCIONCommonHdr()
        chdr.type = pkt_type
        chdr.src_addr_len = src_addr_len
        chdr.dst_addr_len = dst_addr_len
        chdr.next_hdr = next_hdr
        chdr.current_of = chdr.src_addr_len + chdr.dst_addr_len
        chdr.timestamp = chdr.current_of
        chdr.hdr_len = SCIONCommonHdr.LEN + src_addr_len + dst_addr_len
        chdr.total_len = chdr.hdr_len

        return chdr

    def parse(self, raw):
        """
        Parses the raw data and populates the fields accordingly.
        """
        assert isinstance(raw, bytes)
        dlen = len(raw)
        if dlen < SCIONCommonHdr.LEN:
            logging.warning("Data too short to parse SCION common header: "
                            "data len %u", dlen)
            return
        bits = BitArray(bytes=raw)
        (types, self.total_len, self.timestamp, self.current_of,
         self.next_hdr, self.hdr_len) = \
            bits.unpack("uintle:16, uintle:16, uintle:8, "
                        "uintle:8, uintle:8, uintle:8")
        self.type = types & 0xf
        self.src_addr_len = (types >> 4) & 0xf
        self.dst_addr_len = (types >> 10) & 0xf
        self.parsed = True
        return

    def pack(self):
        """
        Returns the common header as 8 byte binary string.
        """
        types = (self.dst_addr_len << 10) | (self.src_addr_len << 4) | self.type
        return bitstring.pack("uintle:16, uintle:16, uintle:8, "
                              "uintle:8, uintle:8, uintle:8",
                              types, self.total_len, self.timestamp,
                              self.current_of, self.next_hdr,
                              self.hdr_len).bytes

    def __str__(self):
        res = ("[CH type: %u, src len: %u, dst len: %u, total len: %u bytes, "
               "TS: %u, current OF: %u, next hdr: %u, hdr len: %u]") % (
               self.type, self.src_addr_len, self.dst_addr_len, self.total_len,
               self.timestamp, self.current_of, self.next_hdr, self.hdr_len)
        return res


class SCIONHeader(HeaderBase):
    """
    The SCION packet header.
    """

    MIN_LEN = 16

    def __init__(self, raw=None):
        HeaderBase.__init__(self)
        self.common_hdr = None
        self.src_addr = None
        self.dst_addr = None
        self.path = None
        self.extension_hdrs = []

        if raw is not None:
            self.parse(raw)

    @classmethod
    def from_values(cls, src, dst, pkt_type, path=None,
                    ext_hdrs=None, next_hdr=0):
        """
        Returns a SCIONHeader with the values specified.
        """
        if ext_hdrs is None:
            ext_hdrs = []
        hdr = SCIONHeader()
        hdr.src_addr = src
        hdr.dst_addr = dst
        hdr.path = path
        hdr.extension_hdrs = ext_hdrs
        hdr.common_hdr = SCIONCommonHdr.from_values(pkt_type, src.addr_len,
                                                    dst.addr_len, next_hdr)
        if path is not None:
            path_len = len(path.pack())
            hdr.common_hdr.hdr_len += path_len
            hdr.common_hdr.total_len += path_len

        for eh in ext_hdrs:
            hdr.common_hdr.total_len += len(eh)

        return hdr

    def parse(self, raw):
        """
        Parses the raw data and populates the fields accordingly.
        """
        assert isinstance(raw, bytes)
        dlen = len(raw)
        if dlen < SCIONHeader.MIN_LEN:
            logging.warning("Data too short to parse SCION header: "
                            "data len %u", dlen)
            return
        offset = 0
        self.common_hdr = \
            SCIONCommonHdr(raw[offset:offset + SCIONCommonHdr.LEN])
        offset += SCIONCommonHdr.LEN
        assert self.common_hdr.parsed

        # Create appropriate HostAddr objects.
        host_types = {AddressLengths.HOST_ADDR_IPV4: IPv4HostAddr,
                      AddressLengths.HOST_ADDR_IPV6: IPv6HostAddr,
                      AddressLengths.HOST_ADDR_SCION: SCIONHostAddr}
        src_addr_len = self.common_hdr.src_addr_len
        self.src_addr = \
            host_types[src_addr_len](raw[offset:offset + src_addr_len])
        offset += src_addr_len
        dst_addr_len = self.common_hdr.dst_addr_len
        self.dst_addr = \
            host_types[dst_addr_len](raw[offset:offset + dst_addr_len])
        offset += dst_addr_len

        # Parse opaque fields.
        info = InfoOpaqueField(raw[offset:offset + InfoOpaqueField.LEN])
        if info.info == PathType.CORE:
            self.path = CorePath(raw[offset:self.common_hdr.hdr_len])
        elif info.info == PathType.CROSS_OVER:
            self.path = CrossOverPath(raw[offset:self.common_hdr.hdr_len])
        elif info.info == PathType.PEER_LINK:
            self.path = PeerPath(raw[offset:self.common_hdr.hdr_len])
        elif info.info == PathType.EMPTY:
            self.path = EmptyPath(raw[offset:self.common_hdr.hdr_len])
        else:
            logging.info("Can not parse path in packet: Unknown type %x",
                         info.info)
        offset = self.common_hdr.hdr_len

        # Parse extensions headers.
        # FIXME: The last extension header should be a layer 4 protocol header.
        # At the moment this is not support and we just indicate the end of the
        # extension headers by a 0 in the type field.
        cur_hdr_type = self.common_hdr.next_hdr
        while cur_hdr_type != 0:
            bits = BitArray(raw[offset: offset + 2])
            (next_hdr_type, hdr_len) = bits.unpack("uintle:8, uintle:8")
            logging.info("Found extension hdr of type %u with len %u",
                         cur_hdr_type, hdr_len)
            # FIXME: Should instantiate correct class depending on ext hdr type.
            if cur_hdr_type == ICNExtHdr.TYPE:
                self.extension_hdrs.append(
                    ICNExtHdr(raw[offset:offset + hdr_len]))
            else:
                self.extension_hdrs.append(
                    ExtensionHeader(raw[offset:offset + hdr_len]))
            cur_hdr_type = next_hdr_type
            offset += hdr_len

        self.parsed = True

    def pack(self):
        """
        Packs the header and returns a byte array.
        """
        data = []
        data.append(self.common_hdr.pack())
        data.append(self.src_addr.addr)
        data.append(self.dst_addr.addr)
        if self.path is not None:
            data.append(self.path.pack())
        for eh in self.extension_hdrs:
            data.append(eh.pack())

        return b"".join(data)

    def get_current_of(self):
        """
        Returns the current opaque field as pointed by the current_of field in
        the common_hdr.
        """
        if self.path is None:
            return None
        offset = (self.common_hdr.current_of - (self.common_hdr.src_addr_len +
                  self.common_hdr.dst_addr_len))
        return self.path.get_of(offset // OpaqueField.LEN)

    def get_next_of(self):
        """
        Returns the opaque field after the one pointed by the current_of field
        in the common hdr or 'None' if there exists no next opaque field.
        """
        if self.path is None:
            return None
        offset = (self.common_hdr.current_of - (self.common_hdr.src_addr_len +
                  self.common_hdr.dst_addr_len))
        return self.path.get_of(offset // OpaqueField.LEN + 1)

    def is_on_up_path(self):
        """
        Returns 'True' if the current opaque field should be interpreted as an
        up-path opaque field and 'False' otherwise.

        Currently this is indicated by a bit in the LSB of the 'type' field in
        the common header.
        """
        return not (self.common_hdr.type & 0x1)

    def __len__(self):
        length = self.common_hdr.hdr_len
        for eh in self.extension_hdrs:
            length += len(eh)
        return length

    def __str__(self):
        s = []
        s.append(str(self.common_hdr) + "\n")
        s.append(str(self.src_addr) + " >> " + str(self.dst_addr) + "\n")
        s.append(str(self.path) + "\n")
        for eh in self.extension_hdrs:
            s.append(str(eh) + "\n")

        return "".join(s)


class SCIONPacket(PacketBase):
    """
    Class for creating and manipulation SCION packets.
    """

    MIN_LEN = 16

    def __init__(self, raw=None):
        PacketBase.__init__(self)
        self.payload_len = 0

        if raw is not None:
            self.parse(raw)

    @classmethod
    def from_values(cls, src, dst, payload, path=None,
                    ext_hdrs=None, next_hdr=0, pkt_type=PacketType.DATA):
        """
        Returns a SCIONPacket with the values specified.

        @param src: Source address (must be a 'HostAddr' object)
        @param dst: Destination address (must be a 'HostAddr' object)
        @param payload: Payload of the packet (either 'bytes' or 'PacketBase')
        @param path: The opaque fields for this packets.
        @param ext_hdrs: A list of extension headers.
        @param next_hdr: If 'ext_hdrs' is not None then this must be the type
                         of the first extension header in the list.
        @param pkt_type: The type of the packet.
        """
        pkt = SCIONPacket()
        pkt.hdr = SCIONHeader.from_values(src, dst, pkt_type, path,
                                          ext_hdrs, next_hdr)
        pkt.payload = payload

        return pkt

    def set_payload(self, payload):
        PacketBase.set_payload(self, payload)
        # Update payload_len and total len of the packet.
        self.hdr.common_hdr.total_len -= self.payload_len
        self.payload_len = len(payload)
        self.hdr.common_hdr.total_len += self.payload_len

    def parse(self, raw):
        """
        Parses the raw data and populates the fields accordingly.
        """
        assert isinstance(raw, bytes)
        dlen = len(raw)
        self.raw = raw
        if dlen < SCIONPacket.MIN_LEN:
            logging.warning("Data too short to parse SCION packet: "
                            "data len %u", dlen)
            return

        self.hdr = SCIONHeader(raw)
        hdr_len = len(self.hdr)
        self.payload_len = dlen - hdr_len
        self.payload = raw[len(self.hdr):]
        self.parsed = True

    def pack(self):
        """
        Packs the header and the payload and returns a byte array.
        """
        data = []
        data.append(self.hdr.pack())
        if isinstance(self.payload, PacketBase):
            data.append(self.payload.pack())
        else:
            data.append(self.payload)

        return b"".join(data)
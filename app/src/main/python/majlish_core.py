import itertools as it
import colorsys
import random
import math
import struct
import shutil
import os
import sys
import tempfile
import uuid
import hashlib
import platform
import subprocess
import requests
import base64
import zlib
import ctypes
import json
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from pathlib import PurePath, Path
from typing import List, Dict, Tuple, Optional, Any
import time
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table
from rich.box import DOUBLE
from rich import print as rprint
from rich.markup import escape
from rich.text import Text
from rich.align import Align
from rich.console import Group
from rich.box import HEAVY_EDGE, ROUNDED, DOUBLE_EDGE
from datetime import datetime
import gmalg
from Crypto.Cipher import AES
from Crypto.Cipher.AES import MODE_CBC
from Crypto.Hash import SHA1
from Crypto.Util.Padding import unpad
from zstandard import ZstdDecompressor, ZstdCompressionDict, DICT_TYPE_AUTO, ZstdCompressor
SKIP_NAMES = {"thumbs.db", ".ds_store", "desktop.ini"}
console = Console()


class SimpleBlockDisplay:
    """Simple display that shows each file and its blocks"""
    
    def __init__(self, total_files: int, pak_name: str):
        self.total_files = total_files
        self.pak_name = pak_name
        self.processed_files = 0
        self.current_file = ""
        self.current_file_idx = 0
        self.all_blocks = []  # Store all blocks for final summary
        self.total_fitted = 0
        self.total_skipped = 0
        
    def start_file(self, file_name: str, total_blocks: int):
        self.current_file_idx += 1
        self.current_file = file_name
        self.current_blocks = []
        self.current_total_blocks = total_blocks
        self.current_fitted = 0
        self.current_skipped = 0
        
        # Print file header
        console.print()
        console.print(f"[bold bright_green]┌─────────────────────────────────────────────────────────────[/bold bright_green]")
        console.print(f"[bold bright_green]│[/] [bold bright_green][{self.current_file_idx}/{self.total_files}][/] [bold bright_green]{file_name}[/bold bright_green] [dim]({total_blocks} blocks)[/dim]")
        console.print(f"[bold bright_green]├─────────────────────────────────────────────────────────────[/bold bright_green]")
        
    def add_block(self, block_idx: int, block_size: int, fitted: bool, compression_ratio: float = None):
        """Add a block result"""
        size_mb = block_size / (1024 * 1024)
        if fitted:
            self.current_fitted += 1
            self.total_fitted += 1
            ratio_str = f" [{compression_ratio:.1%}]" if compression_ratio else ""
            status = f"[bright_green]✓ FITTED{ratio_str}[/bright_green]"
        else:
            self.current_skipped += 1
            self.total_skipped += 1
            status = f"[bright_green]✗ SKIPPED[/bright_green]"
        
        console.print(f"[bold bright_green]│[/]    Block {block_idx:3d}: {size_mb:>7.2f} MB  →  {status}")
        self.current_blocks.append({'fitted': fitted})
        
    def finish_file(self):
        """Finish current file"""
        total_blocks = len(self.current_blocks)
        
        if total_blocks > 0:
            if self.current_fitted == total_blocks:
                status = "[bright_green]✓ ALL FITTED[/bright_green]"
            elif self.current_fitted > 0:
                status = f"[bright_green]✓ {self.current_fitted}/{total_blocks} FITTED[/bright_green]"
            else:
                status = "[bright_green]✗ ALL SKIPPED[/bright_green]"
        else:
            status = "[bright_green]✓ DONE[/bright_green]"
        
        console.print(f"[bold bright_green]└─────────────────────────────────────────────────────────────[/bold bright_green]")
        console.print(f"  [dim]Result: {status}[/dim]")
        
        self.processed_files += 1
        self.all_blocks.extend(self.current_blocks)
        
    def final_summary(self):
        """Print final summary"""
        total_blocks = len(self.all_blocks)
        
        console.print()
        console.print(f"[bold bright_green]╔═════════════════════════════════════════════════════════════════╗[/bold bright_green]")
        console.print(f"[bold bright_green]║[/] [bold bright_green]REPACK SUMMARY[/bold bright_green]")
        console.print(f"[bold bright_green]║[/]")
        console.print(f"[bold bright_green]║[/]   Total Files:   [bold bright_green]{self.processed_files}[/bold bright_green]")
        console.print(f"[bold bright_green]║[/]   Total Blocks:  [bold bright_green]{total_blocks}[/bold bright_green]")
        console.print(f"[bold bright_green]║[/]   Fitted Blocks: [bold bright_green]{self.total_fitted}[/bold bright_green]")
        console.print(f"[bold bright_green]║[/]   Skipped Blocks:[bold bright_green]{self.total_skipped}[/bold bright_green]")
        if total_blocks > 0:
            success_rate = (self.total_fitted / total_blocks) * 100
            console.print(f"[bold bright_green]║[/]   Success Rate:  [bold bright_green]{success_rate:.1f}%[/bold bright_green]")
        console.print(f"[bold bright_green]╚═════════════════════════════════════════════════════════════════╝[/bold bright_green]")

# ==================== ORIGINAL CLASSES (UNCHANGED) ====================

ZUC_KEY = bytes.fromhex('01010101010101010101010101010101')
ZUC_IV = bytes.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')

RSA_MOD_1 = bytes.fromhex('CBE8B9F2504050EF9831B719E9A6249A6D238505ADE909BDE78C180DED6072A0C3347B8AF4780E1F212D952D82D4BF7F233C1ECA499E1F9D9A85B4FAD759F54BABC1666C5DE411EA9E4B2374425DD6C6F54333BBC8F2610FE6063E4D0D6C21A671A8F7C3740555E5DC06D4E1691C456DB4116C0C012BF7B206E8311AAAEC689952BF804EF638F09D5822B4117B114208F14DEB459E80CB770E5B0D7978E21F5E6CED4999D3583108221A7AB28B960277ADB5690A332784019D9C195BE4EA9EA0A09459010F236465DE0D59C3EF7324E954E1118D93EE19F299760C2CDB963CE87973EA5ECC9BBE81C27D4C7C8572AC07E9BCEAC9BD72AB7A56A3C0AD736ABCE4')
RSA_MOD_2 = bytes.fromhex('7F58E8A39A4DA4E87357DDD650EAA16D3B5CE95B213D1030A662566444796A78A84AE9AC3DBFFDE7F41094896696835DAF13B89E6EC2B84963B1B1BAF7151DA245C3FBFAE2A6AE18B2684D03F9229DE2C91440F2A3A3BCDE1E5680C16722A88039C73560D5D43F4B6562C2EEA5B1D926D86B51108A2643C70FB74D6442CE3A08339B8FD8F660AE88129B7AB8C46F2FA58124485CCCB1E987B05A6DA65A01858ED3F89905449AE42BB07290FCB9994BF22E26610BCABB9804783A3B9587917F3D97316EDDA15C5E13F79066407B55A93B291B68A4AC42A98D6E35FED84B14A792D154E62028DDAD20FC301951E5924BE9AD62FB719DD94CC30CAB871BEC4377A8')

SIMPLE1_DECRYPT_KEY = 121
SIMPLE2_DECRYPT_KEY = bytes.fromhex('E55B4ED1')
SIMPLE2_BLOCK_SIZE = 16

SM4_SECRET_4 = 'eb691efea914241317a8'
SM4_SECRET_2 = 'Q0hVTKey$as*1ZFlQCiA'
SM4_SECRET_NEW = [
    'xG2qW5lP7lV2iN5fN5pG',
    'xT1cJ6dL5wC0kK1rB4dK',
    'qC4jS5bZ6fL5xE6nD4zA',
    'gD4jQ2aL3bS3lC3xT0iW',
    'xU1yQ8wE9zY3gZ3bT5aE',
    'uQ3cO2dX7xY4xU7gH7iS',
    'gW1fR0jK6wQ4oN0oK1kZ',
    'aJ4pV7iZ7pU4wP2aC2cZ',
    'cX6jT3cM2oT3vK0kJ1qN',
    'iT2vS0cS6yT6cZ1sE1lO',
    'hM1pH9iY8wM9hT4lN5uJ',
    'kG6bC8jK0fL0dE4sH4mL',
    'dB6lB3vE0eZ8wM8rI0aC',
    'tP7sP7nI9rA2vQ4cV5yQ',
    'aT0cL1yN4pT3sZ7eM2vY',
    'uV6fU8fC9zN3mP5dH8mN',
    'rT6aQ6oZ1yM0gO5tO1aN',
    'jU5bH7lQ0fM9hK2kI0oF',
    'iQ0eM0mJ7uT0kV6kL5zY',
    'rG0lR2rZ5vM6mW5lM1rR',
    'wD2rP3lP9xF4mE1eC5jS',
    'fO3kW1fE6eD0pU1kY7xK',
    'nE1jQ6qK5tW7rM8iD5vV'
]

EM_SIMPLE1 = 1
EM_SIMPLE2 = 16
EM_SM4_2 = 2
EM_SM4_4 = 4
EM_SM4_NEW_BASE = 31
EM_SM4_NEW_MASK = ~EM_SM4_NEW_BASE
EM_UNKNOWN_17 = 17

CM_NONE = 0
CM_ZLIB = 1
CM_ZSTD = 6
CM_ZSTD_DICT = 8
CM_MASK = 15

class SM4:
    _S_BOX = bytes([
        52, 102, 37, 116, 137, 120, 228, 169, 90, 65, 188, 122, 214, 22, 33, 35,
        77, 97, 218, 148, 155, 223, 19, 60, 105, 58, 49, 10, 95, 215, 153, 149,
        241, 174, 114, 61, 7, 96, 36, 182, 152, 238, 196, 162, 45, 136, 221, 141,
        4, 234, 187, 17, 202, 62, 93, 161, 246, 63, 176, 151, 128, 71, 43, 166,
        230, 247, 217, 177, 89, 192, 124, 190, 84, 40, 183, 126, 79, 248, 67, 110,
        160, 80, 14, 245, 144, 184, 251, 163, 123, 98, 25, 70, 3, 42, 185, 143,
        159, 119, 180, 91, 131, 135, 8, 235, 226, 30, 66, 240, 15, 232, 113, 106,
        117, 173, 85, 31, 181, 171, 51, 250, 127, 21, 189, 133, 216, 6, 104, 179,
        82, 48, 72, 11, 0, 237, 239, 178, 87, 142, 231, 108, 213, 229, 46, 83,
        130, 5, 249, 129, 244, 86, 191, 140, 75, 227, 219, 74, 145, 76, 44, 211,
        64, 41, 78, 32, 20, 54, 121, 9, 111, 209, 55, 224, 57, 12, 138, 146,
        56, 18, 53, 109, 225, 253, 147, 154, 23, 212, 201, 156, 107, 132, 38, 157,
        175, 118, 193, 158, 208, 150, 197, 203, 233, 115, 73, 210, 205, 100, 195, 199,
        1, 125, 243, 172, 252, 222, 164, 68, 50, 27, 194, 186, 28, 2, 198, 39,
        69, 139, 242, 24, 167, 16, 81, 29, 200, 207, 99, 255, 47, 13, 88, 206,
        101, 165, 220, 26, 59, 134, 254, 34, 92, 168, 94, 103, 170, 236, 112, 204
    ])
    _FK = [1184304796, 1270900830, 1493524870, 3164752158]
    _CK = [964907, 973793155, 2654690407, 2916866751, 2071233739, 1226140771, 3348805095, 2045549823, 388349611, 800627875, 612403927, 3721562911, 1195432523, 3150178931, 612053223, 2445162591, 67183755, 1174197155, 1393249511, 3331183455, 3822152747, 1332317203, 1804781383, 1990130463, 1282653851, 3376591251, 2910902311, 925872959, 332098219, 735840931, 396665415, 3588844719]
    
    @staticmethod
    def ROL32(x, n):
        return (x << n) & 0xFFFFFFFF | (x >> (32 - n))
    
    @staticmethod
    def _BS(X):
        return (SM4._S_BOX[X >> 24 & 255] << 24 | 
                SM4._S_BOX[X >> 16 & 255] << 16 | 
                SM4._S_BOX[X >> 8 & 255] << 8 | 
                SM4._S_BOX[X & 255])
    
    @staticmethod
    def _T0(X):
        X = SM4._BS(X)
        return X ^ SM4.ROL32(X, 2) ^ SM4.ROL32(X, 10) ^ SM4.ROL32(X, 18) ^ SM4.ROL32(X, 24)
    
    @staticmethod
    def _T1(X):
        X = SM4._BS(X)
        return X ^ SM4.ROL32(X, 13) ^ SM4.ROL32(X, 23)
    
    @staticmethod
    def _key_expand(key: bytes, rkey: list):
        K0 = int.from_bytes(key[0:4], 'big') ^ SM4._FK[0]
        K1 = int.from_bytes(key[4:8], 'big') ^ SM4._FK[1]
        K2 = int.from_bytes(key[8:12], 'big') ^ SM4._FK[2]
        K3 = int.from_bytes(key[12:16], 'big') ^ SM4._FK[3]
        for i in range(0, 32, 4):
            K0 = K0 ^ SM4._T1(K1 ^ K2 ^ K3 ^ SM4._CK[i])
            rkey[i] = K0
            K1 = K1 ^ SM4._T1(K2 ^ K3 ^ K0 ^ SM4._CK[i + 1])
            rkey[i + 1] = K1
            K2 = K2 ^ SM4._T1(K3 ^ K0 ^ K1 ^ SM4._CK[i + 2])
            rkey[i + 2] = K2
            K3 = K3 ^ SM4._T1(K0 ^ K1 ^ K2 ^ SM4._CK[i + 3])
            rkey[i + 3] = K3
    
    @classmethod
    def key_length(cls):
        return 16
    
    @classmethod
    def block_length(cls):
        return 16
    
    def __init__(self, key: bytes):
        if len(key) != self.key_length():
            raise ValueError(f'Key must be {self.key_length()} bytes')
        else:
            self._key = key
            self._rkey = [0] * 32
            SM4._key_expand(self._key, self._rkey)
            self._block_buffer = bytearray()
            if not hasattr(SM4, '_T_TABLES'):
                SM4._T_TABLES = SM4._make_t_tables()
    
    def encrypt(self, block: bytes) -> bytes:
        if len(block) != self.block_length():
            raise ValueError(f'Block must be {self.block_length()} bytes')
        else:
            RK = self._rkey
            X0 = int.from_bytes(block[0:4], 'big')
            X1 = int.from_bytes(block[4:8], 'big')
            X2 = int.from_bytes(block[8:12], 'big')
            X3 = int.from_bytes(block[12:16], 'big')
            for i in range(0, 32, 4):
                X0 = X0 ^ SM4._T0(X1 ^ X2 ^ X3 ^ RK[i])
                X1 = X1 ^ SM4._T0(X2 ^ X3 ^ X0 ^ RK[i + 1])
                X2 = X2 ^ SM4._T0(X3 ^ X0 ^ X1 ^ RK[i + 2])
                X3 = X3 ^ SM4._T0(X0 ^ X1 ^ X2 ^ RK[i + 3])
            BUFFER = self._block_buffer
            BUFFER.clear()
            BUFFER.extend(X3.to_bytes(4, 'big'))
            BUFFER.extend(X2.to_bytes(4, 'big'))
            BUFFER.extend(X1.to_bytes(4, 'big'))
            BUFFER.extend(X0.to_bytes(4, 'big'))
            return bytes(BUFFER)
    
    def decrypt(self, block: bytes) -> bytes:
        if len(block) != self.block_length():
            raise ValueError(f'Block must be {self.block_length()} bytes')
        else:
            RK = self._rkey
            X0 = int.from_bytes(block[0:4], 'big')
            X1 = int.from_bytes(block[4:8], 'big')
            X2 = int.from_bytes(block[8:12], 'big')
            X3 = int.from_bytes(block[12:16], 'big')
            for i in range(0, 32, 4):
                X0 = X0 ^ SM4._T0(X1 ^ X2 ^ X3 ^ RK[31 - i])
                X1 = X1 ^ SM4._T0(X2 ^ X3 ^ X0 ^ RK[30 - i])
                X2 = X2 ^ SM4._T0(X3 ^ X0 ^ X1 ^ RK[29 - i])
                X3 = X3 ^ SM4._T0(X0 ^ X1 ^ X2 ^ RK[28 - i])
            BUFFER = self._block_buffer
            BUFFER.clear()
            BUFFER.extend(X3.to_bytes(4, 'big'))
            BUFFER.extend(X2.to_bytes(4, 'big'))
            BUFFER.extend(X1.to_bytes(4, 'big'))
            BUFFER.extend(X0.to_bytes(4, 'big'))
            return bytes(BUFFER)

    @classmethod
    def _make_t_tables(cls):
        S = cls._S_BOX
        def rol(x, n):
            return (x << n) & 0xFFFFFFFF | (x >> (32 - n))
        def L(y):
            return y ^ rol(y, 2) ^ rol(y, 10) ^ rol(y, 18) ^ rol(y, 24)
        T0 = [0] * 256; T1 = [0] * 256; T2 = [0] * 256; T3 = [0] * 256
        for i in range(256):
            s = S[i]
            T0[i] = L(s << 24)
            T1[i] = L(s << 16)
            T2[i] = L(s << 8)
            T3[i] = L(s)
        return (T0, T1, T2, T3)

    def _bulk(self, data: bytes, rk) -> bytes:
        n = len(data)
        out = bytearray(n)
        T0, T1, T2, T3 = self._T_TABLES
        unpack_from = struct.unpack_from
        pack_into = struct.pack_into
        idx = 0
        while idx < n:
            X0, X1, X2, X3 = unpack_from('>IIII', data, idx)
            for i in range(0, 32, 4):
                t = X1 ^ X2 ^ X3 ^ rk[i]
                X0 ^= T0[t >> 24] ^ T1[t >> 16 & 255] ^ T2[t >> 8 & 255] ^ T3[t & 255]
                t = X2 ^ X3 ^ X0 ^ rk[i + 1]
                X1 ^= T0[t >> 24] ^ T1[t >> 16 & 255] ^ T2[t >> 8 & 255] ^ T3[t & 255]
                t = X3 ^ X0 ^ X1 ^ rk[i + 2]
                X2 ^= T0[t >> 24] ^ T1[t >> 16 & 255] ^ T2[t >> 8 & 255] ^ T3[t & 255]
                t = X0 ^ X1 ^ X2 ^ rk[i + 3]
                X3 ^= T0[t >> 24] ^ T1[t >> 16 & 255] ^ T2[t >> 8 & 255] ^ T3[t & 255]
            pack_into('>IIII', out, idx, X3, X2, X1, X0)
            idx += 16
        return bytes(out)

    def encrypt_bulk(self, data: bytes) -> bytes:
        lib = _load_fast_sm4()
        if lib is not None:
            data = bytes(data)
            n = len(data)
            inbuf = ctypes.create_string_buffer(data)
            outbuf = ctypes.create_string_buffer(n)
            lib.sm4_ecb(ctypes.create_string_buffer(self._key), inbuf, outbuf, n, 1)
            return outbuf.raw
        return self._bulk(data, self._rkey)

    def decrypt_bulk(self, data: bytes) -> bytes:
        lib = _load_fast_sm4()
        if lib is not None:
            data = bytes(data)
            n = len(data)
            inbuf = ctypes.create_string_buffer(data)
            outbuf = ctypes.create_string_buffer(n)
            lib.sm4_ecb(ctypes.create_string_buffer(self._key), inbuf, outbuf, n, 0)
            return outbuf.raw
        return self._bulk(data, self._rkey[::-1])

_FAST_SM4_LIB = None
_FAST_SM4_TRIED = False

def _sm4_c_source() -> str:
    sbox = SM4._S_BOX
    fk = SM4._FK
    ck = SM4._CK
    L = []
    L.append('// auto-generated fast SM4 (GB/T 32907-2016) from tool.py constants')
    L.append('#include <stdint.h>')
    L.append('#include <stddef.h>')
    L.append('')
    L.append('static const uint8_t SBOX[256] = { ' + ', '.join(str(x) for x in sbox) + ' };')
    L.append('static const uint32_t FK[4] = { ' + ', '.join(hex(x) for x in fk) + ' };')
    L.append('static const uint32_t CK[32] = { ' + ', '.join(hex(x) for x in ck) + ' };')
    L.append('')
    L.append('static inline uint32_t rotl(uint32_t x, int n){ return (x << n) | (x >> (32 - n)); }')
    L.append('static inline uint32_t load_be(const uint8_t* p){ return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|(uint32_t)p[3]; }')
    L.append('static inline void store_be(uint8_t* p, uint32_t v){ p[0]=(uint8_t)(v>>24); p[1]=(uint8_t)(v>>16); p[2]=(uint8_t)(v>>8); p[3]=(uint8_t)v; }')
    L.append('static inline uint32_t sb(uint32_t x){ return ((uint32_t)SBOX[(x>>24)&0xff]<<24)|((uint32_t)SBOX[(x>>16)&0xff]<<16)|((uint32_t)SBOX[(x>>8)&0xff]<<8)|(uint32_t)SBOX[x&0xff]; }')
    L.append('static inline uint32_t t0(uint32_t x){ x = sb(x); return x ^ rotl(x,2) ^ rotl(x,10) ^ rotl(x,18) ^ rotl(x,24); }')
    L.append('static inline uint32_t t1(uint32_t x){ x = sb(x); return x ^ rotl(x,13) ^ rotl(x,23); }')
    L.append('')
    L.append('static void expand(const uint8_t* key, uint32_t rk[32]){')
    L.append('    uint32_t k0 = load_be(key) ^ FK[0];')
    L.append('    uint32_t k1 = load_be(key+4) ^ FK[1];')
    L.append('    uint32_t k2 = load_be(key+8) ^ FK[2];')
    L.append('    uint32_t k3 = load_be(key+12) ^ FK[3];')
    L.append('    for (int i = 0; i < 32; i++){')
    L.append('        k0 ^= t1(k1 ^ k2 ^ k3 ^ CK[i]); rk[i] = k0;')
    L.append('        k1 ^= t1(k2 ^ k3 ^ k0 ^ CK[++i]); rk[i] = k1;')
    L.append('        k2 ^= t1(k3 ^ k0 ^ k1 ^ CK[++i]); rk[i] = k2;')
    L.append('        k3 ^= t1(k0 ^ k1 ^ k2 ^ CK[++i]); rk[i] = k3;')
    L.append('    }')
    L.append('}')
    L.append('')
    L.append('static void crypt_block(const uint8_t* in, uint8_t* out, const uint32_t* rk){')
    L.append('    uint32_t x0 = load_be(in);')
    L.append('    uint32_t x1 = load_be(in+4);')
    L.append('    uint32_t x2 = load_be(in+8);')
    L.append('    uint32_t x3 = load_be(in+12);')
    L.append('    for (int i = 0; i < 32; i += 4){')
    L.append('        x0 ^= t0(x1 ^ x2 ^ x3 ^ rk[i]);')
    L.append('        x1 ^= t0(x2 ^ x3 ^ x0 ^ rk[i+1]);')
    L.append('        x2 ^= t0(x3 ^ x0 ^ x1 ^ rk[i+2]);')
    L.append('        x3 ^= t0(x0 ^ x1 ^ x2 ^ rk[i+3]);')
    L.append('    }')
    L.append('    store_be(out, x3); store_be(out+4, x2); store_be(out+8, x1); store_be(out+12, x0);')
    L.append('}')
    L.append('')
    L.append('// ECB transform. encrypt: 1, decrypt: 0. len must be multiple of 16.')
    L.append('void sm4_ecb(const uint8_t* key, const uint8_t* in, uint8_t* out, size_t len, int encrypt){')
    L.append('    uint32_t rk[32];')
    L.append('    expand(key, rk);')
    L.append('    if (!encrypt){')
    L.append('        for (int i = 0; i < 16; i++){ uint32_t tmp = rk[i]; rk[i] = rk[31-i]; rk[31-i] = tmp; }')
    L.append('    }')
    L.append('    for (size_t off = 0; off < len; off += 16){')
    L.append('        crypt_block(in + off, out + off, rk);')
    L.append('    }')
    L.append('}')
    return '\n'.join(L)

def _load_fast_sm4():
    global _FAST_SM4_LIB, _FAST_SM4_TRIED
    if _FAST_SM4_TRIED:
        return _FAST_SM4_LIB
    _FAST_SM4_TRIED = True
    try:
        tool_dir = Path(__file__).resolve().parent
        src_path = tool_dir / 'sm4_fast.c'
        so_path = tool_dir / 'sm4_fast.so'
        c_src = _sm4_c_source()
        if not src_path.exists():
            src_path.write_text(c_src)
        if src_path.read_text() != c_src:
            src_path.write_text(c_src)
        recompile = (not so_path.exists()) or (so_path.stat().st_mtime < src_path.stat().st_mtime)
        if recompile:
            for cc in ('gcc', 'cc', 'clang'):
                try:
                    r = subprocess.run([cc, '-O2', '-shared', '-fPIC', str(src_path), '-o', str(so_path)],
                                       capture_output=True, timeout=120)
                    if r.returncode == 0 and so_path.exists():
                        break
                except Exception:
                    continue
        if not so_path.exists():
            return None
        lib = ctypes.CDLL(str(so_path))
        lib.sm4_ecb.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int]
        lib.sm4_ecb.restype = None
        _FAST_SM4_LIB = lib
        return lib
    except Exception:
        return None

class Misc:
    @staticmethod
    def pad_to_n(data: bytes, n: int) -> bytes:
        assert n > 0
        padding = n - len(data) % n
        if padding == n:
            return data
        else:
            return data + b'\x00' * padding
    @staticmethod
    def align_up(x: int, n: int) -> int:
        return (x + n - 1) // n * n

class Reader:
    def __init__(self, buffer, cursor=0):
        self._buffer = buffer
        self._cursor = cursor
    def u1(self, move_cursor=True) -> int:
        return self.unpack('B', move_cursor=move_cursor)[0]
    def u4(self, move_cursor=True) -> int:
        return self.unpack('<I', move_cursor=move_cursor)[0]
    def u8(self, move_cursor=True) -> int:
        return self.unpack('<Q', move_cursor=move_cursor)[0]
    def i1(self, move_cursor=True) -> int:
        return self.unpack('b', move_cursor=move_cursor)[0]
    def i4(self, move_cursor=True) -> int:
        return self.unpack('<i', move_cursor=move_cursor)[0]
    def i8(self, move_cursor=True) -> int:
        return self.unpack('<q', move_cursor=move_cursor)[0]
    def s(self, n: int, move_cursor=True) -> bytes:
        return self.unpack(f'{n}s', move_cursor=move_cursor)[0]
    def unpack(self, f: str, offset=0, move_cursor=True):
        x = struct.unpack_from(f, self._buffer, self._cursor + offset)
        if move_cursor:
            self._cursor += struct.calcsize(f)
        return x
    def string(self, move_cursor=True) -> str:
        length = self.i4(move_cursor=move_cursor)
        if length == 0:
            return str()
        else:
            assert length > 0
            offset = 0 if move_cursor else 4
            return self.unpack(f'{length}s', offset=offset, move_cursor=move_cursor)[0].rstrip(b'\x00').decode()

class PakInfo:
    def __init__(self, buffer, keystream: List[int]):
        def decrypt_index_encrypted(x: int) -> int:
            MASK_8 = 255
            return (x ^ keystream[3]) & MASK_8
        def decrypt_magic(x: int) -> int:
            return x ^ keystream[2]
        def decrypt_index_hash(x: bytes) -> bytes:
            key = struct.pack('<5I', *keystream[4:][:5])
            assert len(x) == len(key)
            return bytes((a ^ b for a, b in zip(x, key)))
        def decrypt_index_size(x: int) -> int:
            return x ^ (keystream[10] << 32 | keystream[11])
        def decrypt_index_offset(x: int) -> int:
            return x ^ (keystream[0] << 32 | keystream[1])
        reader = Reader(buffer[-PakInfo._mem_size((-1)):])
        self.index_encrypted = decrypt_index_encrypted(reader.u1()) == 1
        self.magic = decrypt_magic(reader.u4())
        self.version = reader.u4()
        self.index_hash = decrypt_index_hash(reader.s(20)) if self.version >= 6 else bytes()
        self.index_size = decrypt_index_size(reader.u8())
        self.index_offset = decrypt_index_offset(reader.u8())
        if self.version <= 3:
            self.index_encrypted = False
    @staticmethod
    def _mem_size(_: int) -> int:
        return 45

class TencentPakInfo(PakInfo):
    def __init__(self, buffer, keystream: List[int]):
        def decrypt_unk(x: bytes) -> bytes:
            key = struct.pack('<8I', *keystream[7:][:8])
            assert len(x) == len(key)
            return bytes((a ^ b for a, b in zip(x, key)))
        def decrypt_stem_hash(x: int) -> int:
            return x ^ keystream[8]
        def decrypt_unk_hash(x: int) -> int:
            return x ^ keystream[9]
        super().__init__(buffer, keystream)
        reader = Reader(buffer[-TencentPakInfo._mem_size(self.version):])
        self.unk1 = decrypt_unk(reader.s(32)) if self.version >= 7 else bytes()
        self.packed_key = reader.s(256) if self.version >= 8 else bytes()
        self.packed_iv = reader.s(256) if self.version >= 8 else bytes()
        self.packed_index_hash = reader.s(256) if self.version >= 8 else bytes()
        self.stem_hash = decrypt_stem_hash(reader.u4()) if self.version >= 9 else 0
        self.unk2 = decrypt_unk_hash(reader.u4()) if self.version >= 9 else 0
        self.content_org_hash = reader.s(20) if self.version >= 12 else bytes()
    @staticmethod
    def _mem_size(version: int) -> int:
        size_for_7 = 32 if version >= 7 else 0
        size_for_8 = 768 if version >= 8 else 0
        size_for_9 = 8 if version >= 9 else 0
        size_for_12 = 20 if version >= 12 else 0
        return PakInfo._mem_size(version) + size_for_7 + size_for_8 + size_for_9 + size_for_12

class PakCompressedBlock:
    def __init__(self, reader: Reader):
        self.start = reader.u8()
        self.end = reader.u8()

@dataclass
class TencentPakEntry:
    def __init__(self, reader: Reader, version: int):
        self.content_hash = reader.s(20)
        if version <= 1:
            _ = reader.u8()
        self.offset = reader.u8()
        self.uncompressed_size = reader.u8()
        self.compression_method = reader.u4() & CM_MASK
        self.size = reader.u8()
        self.unk1 = reader.u1() if version >= 5 else 0
        self.unk2 = reader.s(20) if version >= 5 else bytes()
        if self.compression_method != 0 and version >= 3:
            self.compressed_blocks = [PakCompressedBlock(reader) for _ in range(reader.u4())]
        else:
            self.compressed_blocks = []
        self.compression_block_size = reader.u4() if version >= 4 else 0
        self.encrypted = reader.u1() == 1 if version >= 4 else False
        self.encryption_method = reader.u4() if version >= 12 else 0
        self.index_new_sep = reader.u4() if version >= 12 else 0

class PakCrypto:
    class _LCG:
        def __init__(self, seed: int):
            self.state = seed
        def next(self) -> int:
            MASK_32 = 4294967295
            MSB_1 = 2147483648
            def wrap(x: int) -> int:
                x &= MASK_32
                if not x & MSB_1:
                    return x
                else:
                    return (x + MSB_1 & MASK_32) - MSB_1
            x1 = wrap(1103515245 * self.state)
            self.state = wrap(x1 + 12345)
            x2 = wrap(x1 + 77880) if self.state < 0 else self.state
            return (x2 >> 16 & MASK_32) % 32767
    @staticmethod
    def zuc_keystream() -> List[int]:
        zuc = gmalg.ZUC(ZUC_KEY, ZUC_IV)
        return [struct.unpack('>I', zuc.generate())[0] for _ in range(16)]
    @staticmethod
    def _xorxor(buffer, x) -> bytes:
        return bytes((buffer[i] ^ x[i % len(x)] for i in range(len(buffer))))
    @staticmethod
    def _hashhash(buffer, n: int) -> bytes:
        result = bytes()
        for i in range(math.ceil(n / SHA1.digest_size)):
            result += SHA1.new(buffer).digest()
        if len(result) >= n:
            result = result[:n]
            return result
        else:
            result += b'\x00' * (n - len(result))
            return result
    @staticmethod
    def _meowmeow(buffer) -> bytes:
        def unpad(x):
            skip = 1 + next((i for i in range(len(x)) if x[i]!= 0))
            return x[skip:]
        if len(buffer) < 43:
            return bytes()
        else:
            x1 = buffer[1:][:SHA1.digest_size]
            x2 = buffer[SHA1.digest_size + 1:]
            x1 = PakCrypto._xorxor(x1, PakCrypto._hashhash(x2, len(x1)))
            x2 = PakCrypto._xorxor(x2, PakCrypto._hashhash(x1, len(x2)))
            part1, m = (x2[:SHA1.digest_size], x2[SHA1.digest_size:])
            if part1!= SHA1.new(b'\x00' * SHA1.digest_size).digest():
                return bytes()
            else:
                return unpad(m)
    @staticmethod
    def rsa_extract(signature: bytes, modulus: bytes) -> bytes:
        c = int.from_bytes(signature, 'little')
        n = int.from_bytes(modulus, 'little')
        e = 65537
        m = pow(c, e, n).to_bytes(256, 'little').rstrip(b'\x00')
        return PakCrypto._meowmeow(Misc.pad_to_n(m, 4))
    @staticmethod
    def _decrypt_simple1(ciphertext) -> bytes:
        return bytes((x ^ SIMPLE1_DECRYPT_KEY for x in ciphertext))
    @staticmethod
    def _decrypt_simple2(ciphertext) -> bytes:
        class RollingKey:
            def __init__(self, initial_value: int):
                self._value = initial_value
            def update(self, x: int) -> int:
                self._value ^= x
                return self._value
        assert len(ciphertext) % SIMPLE2_BLOCK_SIZE == 0
        initial_key, = struct.unpack('<I', SIMPLE2_DECRYPT_KEY)
        rolling_key = RollingKey(initial_key)
        plaintext = (struct.pack('<I', rolling_key.update(x)) for x in struct.unpack(f'<{len(ciphertext) // 4}I', ciphertext))
        return bytes(it.chain.from_iterable(plaintext))
    @staticmethod
    @lru_cache(maxsize=4096)
    def _derive_sm4_key(file_path: PurePath, encryption_method: int) -> bytes:
        part1 = file_path.stem.lower()
        if encryption_method == EM_SM4_2:
            secret = SM4_SECRET_2
        elif encryption_method == EM_SM4_4:
            secret = SM4_SECRET_4
        elif encryption_method == EM_UNKNOWN_17:
            index = (encryption_method - EM_SM4_NEW_BASE) % len(SM4_SECRET_NEW)
            secret = SM4_SECRET_NEW[index]
        else:
            index = (encryption_method - EM_SM4_NEW_BASE) % len(SM4_SECRET_NEW)
            secret = f'{SM4_SECRET_NEW[index]}{encryption_method}'
        return SHA1.new(str(part1 + secret).encode()).digest()[:SM4.key_length()]
    @staticmethod
    @lru_cache(maxsize=4096)
    def _sm4_context_for_key(key: bytes) -> SM4:
        return SM4(key)
    @staticmethod
    def _decrypt_sm4(ciphertext, file_path: PurePath, encryption_method: int) -> bytes:
        assert len(ciphertext) % SM4.block_length() == 0
        key = PakCrypto._derive_sm4_key(file_path, encryption_method)
        sm4 = PakCrypto._sm4_context_for_key(key)
        return sm4.decrypt_bulk(ciphertext)
    @staticmethod
    def decrypt_index(ciphertext, pak_info: TencentPakInfo) -> bytes:
        if pak_info.version > 7:
            key = PakCrypto.rsa_extract(pak_info.packed_key, RSA_MOD_1)
            iv = PakCrypto.rsa_extract(pak_info.packed_iv, RSA_MOD_1)
            assert len(key) == 32 and len(iv) == 32
            aes = AES.new(key, MODE_CBC, iv[:16])
            return unpad(aes.decrypt(ciphertext), AES.block_size)
        else:
            return bytes(PakCrypto._decrypt_simple1(ciphertext))
    @staticmethod
    def _is_simple1_method(encryption_method: int) -> bool:
        return encryption_method == EM_SIMPLE1
    @staticmethod
    def _is_simple2_method(encryption_method: int) -> bool:
        return encryption_method == EM_SIMPLE2
    @staticmethod
    def _is_sm4_method(encryption_method: int) -> bool:
        return encryption_method == EM_SM4_2 or encryption_method == EM_SM4_4 or encryption_method == EM_UNKNOWN_17 or encryption_method & EM_SM4_NEW_MASK!= 0
    @staticmethod
    def align_encrypted_content_size(n: int, encryption_method: int) -> int:
        if PakCrypto._is_simple2_method(encryption_method):
            return Misc.align_up(n, SIMPLE2_BLOCK_SIZE)
        else:
            if PakCrypto._is_sm4_method(encryption_method):
                return Misc.align_up(n, SM4.block_length())
            else:
                return n
    @staticmethod
    def decrypt_block(ciphertext, file: PurePath, encryption_method: int) -> bytes:
        if PakCrypto._is_simple1_method(encryption_method):
            return PakCrypto._decrypt_simple1(ciphertext)
        else:
            if PakCrypto._is_simple2_method(encryption_method):
                return PakCrypto._decrypt_simple2(ciphertext)
            else:
                if PakCrypto._is_sm4_method(encryption_method):
                    return PakCrypto._decrypt_sm4(ciphertext, file, encryption_method)
                else:
                    raise ValueError(f'Unknown encryption method: {encryption_method}')
    @staticmethod
    @lru_cache(maxsize=33)
    def generate_block_indices(n: int, encryption_method: int) -> List[int]:
        if not PakCrypto._is_sm4_method(encryption_method):
            return list(range(n))
        else:
            permutation = []
            lcg = PakCrypto._LCG(n)
            while len(permutation)!= n:
                x = lcg.next() % n
                if x not in permutation:
                    permutation.append(x)
            inverse = [0] * len(permutation)
            for i, x in enumerate(permutation):
                inverse[x] = i
            return inverse

class PakCompression:
    @staticmethod
    @lru_cache(maxsize=33)
    def _zstd_decompressor(dict: ZstdCompressionDict) -> ZstdDecompressor:
        return ZstdDecompressor(dict)
    @staticmethod
    def zstd_dictionary(dict_data) -> ZstdCompressionDict:
        return ZstdCompressionDict(dict_data, DICT_TYPE_AUTO)
    @staticmethod
    def decompress_block(block, dict: Optional[ZstdCompressionDict], compression_method: int) -> bytes:
        if compression_method == CM_ZLIB:
            try:
                return zlib.decompress(block)
            except zlib.error:
                return block
        else:
            if compression_method == CM_ZSTD or compression_method == CM_ZSTD_DICT:
                if compression_method!= CM_ZSTD_DICT:
                    dict = None
                return PakCompression._zstd_decompressor(dict).decompress(block)
            else:
                raise ValueError(f'Unknown compression method: {compression_method}')

class TencentPakFile:
    def __init__(self, file_path: PurePath, is_od=False):
        self._file_path = file_path
        with open(file_path, 'rb') as file:
            self._file_content = memoryview(file.read())
        self._is_od = is_od
        self._mount_point = PurePath()
        self._is_zstd_with_dict = 'zsdic' in str(self._file_path)
        self._zstd_dict = None
        self._zstd_dict_entry = None
        self._files = []
        self._index = {}
        self._pak_info = TencentPakInfo(self._file_content, PakCrypto.zuc_keystream())
        self._verify_stem_hash()
        self._tencent_load_index()
    
    def _get_method_str(self, method_int, is_encryption):
        if is_encryption:
            if method_int == EM_UNKNOWN_17: return "ENC17?"
            if PakCrypto._is_simple1_method(method_int): return "SIMPLE1"
            if PakCrypto._is_simple2_method(method_int): return "SIMPLE2"
            if PakCrypto._is_sm4_method(method_int): return f"SM4 (Type {method_int})"
            return "NONE" if method_int == 0 else "UNKNOWN"
        else:
            if method_int == CM_NONE: return "NONE"
            if method_int == CM_ZLIB: return "ZLIB"
            if method_int == CM_ZSTD: return "ZSTD"
            if method_int == CM_ZSTD_DICT: return "ZSTD_DICT"
            return "UNKNOWN"
    
    def _verify_stem_hash(self) -> None:
        if not self._is_od and self._pak_info.version >= 9:
            try:
                assert self._pak_info.stem_hash == zlib.crc32(self._file_path.stem.encode('utf-32le'))
            except AssertionError:
                print(f"⚠ Warning: pak filename differs from original stem; rename back to match before game use.")
    def _tencent_load_index(self) -> None:
        index_data = self._file_content[self._pak_info.index_offset:][:self._pak_info.index_size]
        if self._pak_info.index_encrypted:
            index_data = PakCrypto.decrypt_index(index_data, self._pak_info)
        else:
            index_data = index_data
        self._verify_index_hash(index_data)
        self._load_index(index_data)
    def _verify_index_hash(self, index_data) -> None:
        expected_hash = self._pak_info.index_hash
        if not self._is_od and self._pak_info.version >= 8:
            if expected_hash != PakCrypto.rsa_extract(self._pak_info.packed_index_hash, RSA_MOD_2):
                console.print(f"[bold bright_green]![/] [bright_green]packed_index_hash mismatch "
                              f"(rebuilt pak - stale RSA blob, ignored)[/bright_green]")
        assert expected_hash == SHA1.new(index_data).digest()
    @staticmethod
    def _construct_mount_point(mount_point: str) -> PurePath:
        result = PurePath()
        for part in PurePath(mount_point).parts:
            if part!= '..':
                result /= part
        return result
    def _peek_content(self, offset: int, size: int, encryption_method: int) -> memoryview:
        size = PakCrypto.align_encrypted_content_size(size, encryption_method)
        return self._file_content[offset:][:size]
    def _peek_block_content(self, block: PakCompressedBlock, encryption_method: int) -> memoryview:
        size = PakCrypto.align_encrypted_content_size(block.end - block.start, encryption_method)
        return self._file_content[block.start:][:size]
    def _construct_zstd_dict(self, dict_entry: TencentPakEntry) -> None:
        assert not self._zstd_dict
        assert not dict_entry.encrypted
        assert dict_entry.compression_method == CM_NONE
        reader = Reader(self._peek_content(dict_entry.offset, dict_entry.size, 0))
        dict_size = reader.u8()
        _ = reader.u4()
        assert dict_size == reader.u4()
        dict_data = reader.s(dict_size)
        self._zstd_dict = PakCompression.zstd_dictionary(dict_data)
    def _load_index(self, index_data) -> None:
        if self._pak_info.version <= 10:
            raise ValueError(f'Unsupported version: {self._pak_info.version}')
        else:
            reader = Reader(index_data)
            self._mount_point = self._construct_mount_point(reader.string())
            self._files = [TencentPakEntry(reader, self._pak_info.version) for _ in range(reader.u4())]
            for _ in range(reader.u8()):
                dir_path = PurePath(reader.string())
                e = {reader.string(): self._files[~reader.i4()] for _ in range(reader.u8())}
                if self._is_zstd_with_dict and dir_path.name == 'zstddic':
                    assert len(e) == 1
                    self._zstd_dict_entry = e[[*e.keys()][0]]
                    self._construct_zstd_dict(self._zstd_dict_entry)
                else:
                    self._index.update({PurePath(dir_path): e})
    
    def _write_to_disk(self, file_path: Path, entry: TencentPakEntry) -> None:
        encryption_method = entry.encryption_method
        compression_method = entry.compression_method

        enc_str = self._get_method_str(encryption_method, True)
        comp_str = self._get_method_str(compression_method, False)
        console.print(f"[bold bright_green]->[/] Unpack: [bold bright_green]{file_path.name}[/] [[bold bright_green]{comp_str}[/]/[bold green]{enc_str}[/]]")

        # ENC 17 cipher is unknown — never try to decrypt silently, raw-dump it.
        if entry.encrypted and encryption_method == EM_UNKNOWN_17:
            self._dump_raw_unsupported_17(file_path, entry)
            return
        # Validate first block for SM4 types: wrong key => garbage => ZstdError.
        # Probe before writing so user sees clear message instead of generic dump.
        if entry.encrypted and entry.compression_method != CM_NONE and PakCrypto._is_sm4_method(encryption_method):
            try:
                if entry.compressed_blocks:
                    probe_idx = next(iter(PakCrypto.generate_block_indices(len(entry.compressed_blocks), encryption_method)))
                    probe = bytes(self._peek_block_content(entry.compressed_blocks[probe_idx], encryption_method))
                    probe = PakCrypto.decrypt_block(probe, file_path, encryption_method)
                    if not self._decrypted_looks_valid(bytes(probe), compression_method):
                        raise ValueError(f'Decrypt probe failed (wrong SM4 key for Type {encryption_method})')
            except Exception as exc:
                with open(file_path, 'wb') as _f:
                    raw = bytearray()
                    for blk in entry.compressed_blocks:
                        raw += bytes(self._peek_block_content(blk, encryption_method))
                    _f.write(raw)
                console.print(f"[bold bright_green]![/] [bright_green]Raw dump for undecryptable file[/] "
                              f"[bold bright_green]{file_path.name}[/] "
                              f"[dim]({type(exc).__name__}: {exc})[/dim]")
                return

        with open(file_path, 'wb') as file:
            if compression_method == CM_NONE:
                data = self._peek_content(entry.offset, entry.size, encryption_method)
                if entry.encrypted:
                    data = PakCrypto.decrypt_block(data, file_path, encryption_method)
                data = bytes(data)
                if entry.uncompressed_size and len(data) > entry.uncompressed_size:
                    data = data[:entry.uncompressed_size]
                file.write(data)
                return
            else:
                try:
                    for x in PakCrypto.generate_block_indices(len(entry.compressed_blocks), encryption_method):
                        data = self._peek_block_content(entry.compressed_blocks[x], encryption_method)
                        if entry.encrypted:
                            data = PakCrypto.decrypt_block(data, file_path, encryption_method)
                        data = PakCompression.decompress_block(data, self._zstd_dict, compression_method)
                        file.write(data)
                except Exception as exc:
                    file.seek(0)
                    file.truncate()
                    raw = bytearray()
                    for blk in entry.compressed_blocks:
                        raw += self._peek_block_content(blk, encryption_method)
                    file.write(raw)
                    console.print(f"[bold bright_green]![/] [bright_green]Raw dump for undecryptable file[/] "
                                  f"[bold bright_green]{file_path.name}[/] "
                                  f"[dim]({type(exc).__name__})[/dim]")

    @staticmethod
    def _decrypted_looks_valid(data: bytes, compression_method: int) -> bool:
        """True if decrypted bytes look like a real compressed stream."""
        if compression_method == CM_ZLIB:
            return len(data) >= 2 and data[0] == 0x78 and data[1] in (0x01, 0x9C, 0xDA)
        if compression_method in (CM_ZSTD, CM_ZSTD_DICT):
            return bytes(data[:4]) == b'\x28\xb5\x2f\xfd'
        return True

    def _dump_raw_unsupported_17(self, file_path: Path, entry: TencentPakEntry) -> None:
        console.print(f"[bold bright_green]⚠ ENC 17 UNSUPPORTED ({file_path.name}) — cipher unknown, dumped raw encrypted bytes.[/bold bright_green]")
        with open(file_path, 'wb') as file:
            if entry.compression_method == CM_NONE:
                file.write(bytes(self._peek_content(entry.offset, entry.size, entry.encryption_method)))
            else:
                for blk in entry.compressed_blocks:
                    file.write(bytes(self._file_content[blk.start:blk.end]))
    
    def dump(self, out_path: Path) -> None:
        out_path = out_path / self._mount_point
        out_path.mkdir(parents=True, exist_ok=True)
        total_files = sum(len(d) for d in self._index.values())
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold bright_green][UNPACK][/] {task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Extracting files...", total=total_files)
            for dir_path, dir_content in self._index.items():
                current_out_path = out_path / dir_path
                current_out_path.mkdir(parents=True, exist_ok=True)
                for file_name, entry in dir_content.items():
                    self._write_to_disk(current_out_path / file_name, entry)
                    progress.update(task, advance=1)

def dump_unpacking_log(pak_file, output_log_path: Path):
    with open(output_log_path, 'w', encoding='utf-8') as log_file:
        log_file.write('================================================================================\n')
        log_file.write('PAK UNPACKING DEBUG LOG\n')
        log_file.write('================================================================================\n\n')
        log_file.write(f'PAK File: {pak_file._file_path}\n')
        log_file.write(f'PAK Info Version: {pak_file._pak_info.version}\n')
        log_file.write(f'Mount Point: {pak_file._mount_point}\n')
        log_file.write('--------------------------------------------------------------------------------\n\n')
        file_count = 0
        for dir_path, files in pak_file._index.items():
            for file_name, entry in files.items():
                file_count += 1
                full_path = str(PurePath(dir_path) / file_name).replace('\\', '/')
                log_file.write(f'\n[{file_count}] {full_path}\n')
                log_file.write(f'  Uncompressed Size: {entry.uncompressed_size:,} bytes\n')
                log_file.write(f'  Compressed Size: {entry.size:,} bytes\n')
                log_file.write(f'  Compression Method: {entry.compression_method}\n')
                log_file.write(f'  Encryption Method: {entry.encryption_method}\n')
                log_file.write(f'  Compressed Blocks: {len(entry.compressed_blocks)}\n')
                if entry.compressed_blocks:
                    for i, blk in enumerate(entry.compressed_blocks):
                        block_size = blk.end - blk.start
                        log_file.write(f'    Block {i}: Offset={blk.start:,} Size={block_size:,} bytes\n')
        log_file.write('\n================================================================================\n')
        log_file.write('END OF LOG\n')
        log_file.write('================================================================================\n')
    console.print(f'[bold #00FF88]✅ Debug log saved to: {output_log_path}[/bold #00FF88]')

def _zstd_add_skippable_padding(data: bytes, pad_len: int) -> bytes:
    if pad_len <= 0:
        return data
    else:
        out = bytearray(data)
        while pad_len > 0:
            frame_len = min(max(pad_len - 8, 0), 1048576)
            out += b'P*M\x18'
            out += struct.pack('<I', frame_len)
            out += b'\x00' * frame_len
            pad_len -= 8 + frame_len
        return bytes(out)


def _encrypt_plaintext(plaintext: bytes, pak_relative_path: PurePath, encryption_method: int) -> bytes:
    if PakCrypto._is_simple1_method(encryption_method):
        return bytes((b ^ SIMPLE1_DECRYPT_KEY for b in plaintext))
    else:
        if PakCrypto._is_simple2_method(encryption_method):
            pad = -len(plaintext) % SIMPLE2_BLOCK_SIZE
            plaintext += b'\x00' * pad
            key, = struct.unpack('<I', SIMPLE2_DECRYPT_KEY)
            rolling = key
            out = []
            for x, in struct.iter_unpack('<I', plaintext):
                c = rolling ^ x
                out.append(c)
                rolling ^= c
            return struct.pack(f'<{len(out)}I', *out)
        else:
            if PakCrypto._is_sm4_method(encryption_method):
                key = PakCrypto._derive_sm4_key(pak_relative_path, encryption_method)
                sm4 = PakCrypto._sm4_context_for_key(key)
                pad_len = -len(plaintext) % 16
                if pad_len > 0:
                    plaintext = plaintext + b'\x00' * pad_len
                return sm4.encrypt_bulk(plaintext)
            else:
                return plaintext

# ==================== WORKING REPACK FUNCTIONS ====================

def _repack_uncompressed(outfh, pak_file, entry, pak_relative_path: PurePath, new_data: bytes):
    enc_method = entry.encryption_method
    target_size = entry.size
    enc_region = PakCrypto.align_encrypted_content_size(target_size, enc_method) if entry.encrypted else target_size
    plaintext = new_data[:enc_region]
    if entry.encrypted:
        a = PakCrypto.align_encrypted_content_size(len(plaintext), enc_method)
        plaintext += b'\x00' * (a - len(plaintext))
        cipher = _encrypt_plaintext(plaintext, pak_relative_path, enc_method)
        outfh.seek(entry.offset)
        outfh.write(cipher)
        with open(pak_file._file_path, 'rb') as src:
            src.seek(entry.offset + len(cipher))
            outfh.write(src.read(enc_region - len(cipher)))
    else:
        outfh.seek(entry.offset)
        outfh.write(plaintext)
        with open(pak_file._file_path, 'rb') as src:
            src.seek(entry.offset + len(plaintext))
            outfh.write(src.read(target_size - len(plaintext)))

def _best_compress(chunk, cm, zstd_dict=None, fast=False):
    """Compress one chunk. fast=True (protect path) uses quick levels."""
    if cm == CM_ZLIB:
        return zlib.compress(chunk, 1 if fast else 9)
    if cm in (CM_ZSTD, CM_ZSTD_DICT):
        zd = zstd_dict if cm == CM_ZSTD_DICT else None
        levels = [6, 3, 1] if fast else [22, 19, 16, 13, 10, 7, 4, 1]
        for lvl in levels:
            try:
                return ZstdCompressor(level=lvl, dict_data=zd, threads=1).compress(chunk)
            except Exception:
                continue
    return chunk  # fallback: store raw

def _pw_string(s):
    """PAK string serialiser: i4(len_with_null) + bytes + null."""
    if not s: return struct.pack('<i', 0)
    b = s.encode('utf-8') + b'\x00'
    return struct.pack('<i', len(b)) + b

def _pw_entry(e, v):
    """Serialise one TencentPakEntry back to bytes."""
    w = bytearray(e.content_hash)
    w += struct.pack('<Q', e.offset)
    w += struct.pack('<Q', e.uncompressed_size)
    w += struct.pack('<I', e.compression_method)
    w += struct.pack('<Q', e.size)
    if v >= 5:
        w += bytes([e.unk1])
        w += e.unk2  # 20 bytes
    if e.compression_method != CM_NONE and v >= 3:
        w += struct.pack('<I', len(e.compressed_blocks))
        for b in e.compressed_blocks:
            w += struct.pack('<QQ', b.start, b.end)
    if v >= 4:
        w += struct.pack('<I', e.compression_block_size)
        w += bytes([1 if e.encrypted else 0])
    if v >= 12:
        w += struct.pack('<II', e.encryption_method, e.index_new_sep)
    return bytes(w)

def _get_all_dirs_and_mp(pak_file):
    """Re-parse raw (possibly encrypted) index → (mount_point_str, ordered dirs dict)."""
    raw = bytes(pak_file._file_content[
        pak_file._pak_info.index_offset:][:pak_file._pak_info.index_size])
    if pak_file._pak_info.index_encrypted:
        raw = PakCrypto.decrypt_index(raw, pak_file._pak_info)
    r = Reader(raw)
    mp = r.string()
    num_files = r.u4()
    for _ in range(num_files):
        TencentPakEntry(r, pak_file._pak_info.version)
    dirs = {}
    for _ in range(r.u8()):
        dp = r.string()
        cnt = r.u8()
        dirs[dp] = {r.string(): pak_file._files[~r.i4()] for _ in range(cnt)}
    return mp, dirs

def repack_pak_file_full(pak_file, edited_root, output_path, target_path=None, force_add=False):
    """
    FULL REBUILD REPACK - FIXED FOR NEW FILES (OPTION 4)
    """
    import copy as _cp

    console.print(f'[bold bright_green]📦 Full PAK Rebuild mode (Option 3 & 4 logic)[/bold bright_green]')
    if target_path:
        console.print(f'[bold bright_green]🎯 Target path: {target_path}[/bold bright_green]')
    
    # Get all files from edit folder
    edit_files = []
    for p in Path(edited_root).rglob('*'):
        if p.is_file():
            edit_files.append(p)
    
    if not edit_files:
        console.print('[bold bright_green]❌ No files found in EDIT folder![/bold bright_green]')
        return 0
    
    console.print(f'[bold bright_green]📁 Found {len(edit_files)} files in EDIT folder[/bold bright_green]')

    version = pak_file._pak_info.version
    keystream = PakCrypto.zuc_keystream()
    orig_fc = pak_file._file_content

    # Get existing directory structure
    mp_str, all_dirs = _get_all_dirs_and_mp(pak_file)

    # FIX 1: Normalize target_path to match exact case and slashes of existing dirs
    if target_path and force_add:
        target_path = target_path.replace('\\', '/')
        matched_dir = None
        for existing_dir in all_dirs.keys():
            if existing_dir.strip('/').lower() == target_path.strip('/').lower():
                matched_dir = existing_dir
                break
        if matched_dir:
            target_path = matched_dir # Use the exact string from the PAK
        else:
            target_path = target_path.strip('/') + '/' # Ensure standard trailing slash
    
    # Build name→entry map
    pak_name_map = {}
    for dir_path, files in pak_file._index.items():
        for name, entry in files.items():
            full_path = str(PurePath(dir_path)/name).replace('\\', '/')
            pak_name_map.setdefault(name.lower(), []).append((full_path, entry))

    # Find matching files
    edited = {}
    
    for p in edit_files:
        fl = p.name.lower()
        found_match = False
        
        if fl in pak_name_map:
            cands = pak_name_map[fl]
            if target_path:
                target_candidates = [(fp, e) for fp, e in cands if target_path.strip('/') in fp]
                if target_candidates:
                    sz = p.stat().st_size
                    sm = [(fp, e) for fp, e in target_candidates if e.uncompressed_size == sz]
                    fp, ent = sm[0] if sm else target_candidates[0]
                    edited[fp] = (p, ent)
                    found_match = True
            
            if not found_match:
                sz = p.stat().st_size
                sm = [(fp, e) for fp, e in cands if e.uncompressed_size == sz]
                fp, ent = sm[0] if sm else cands[0]
                if target_path:
                    new_fp = f"{target_path.rstrip('/')}/{p.name}"
                    edited[new_fp] = (p, ent)
                else:
                    edited[fp] = (p, ent)
                found_match = True
        
        if not found_match:
            stem = p.stem.lower()
            ext = p.suffix.lower()
            for dir_path, files in pak_file._index.items():
                for name, entry in files.items():
                    if Path(name).stem.lower() == stem and Path(name).suffix.lower() == ext:
                        full_path = str(PurePath(dir_path)/name).replace('\\', '/')
                        if target_path:
                            new_fp = f"{target_path.rstrip('/')}/{p.name}"
                            edited[new_fp] = (p, entry)
                        else:
                            edited[full_path] = (p, entry)
                        found_match = True
                        break
                if found_match:
                    break
        
        if not found_match and force_add and target_path:
            template_entry = None
            for dir_path, files in pak_file._index.items():
                for name, entry in files.items():
                    if Path(name).suffix.lower() == p.suffix.lower():
                        template_entry = entry
                        break
                if template_entry: break
            
            if not template_entry:
                for dir_path, files in pak_file._index.items():
                    for name, entry in files.items():
                        template_entry = entry
                        break
                    if template_entry: break
            
            if template_entry:
                new_fp = f"{target_path.rstrip('/')}/{p.name}"
                edited[new_fp] = (p, template_entry)

    if not edited:
        console.print('[bold bright_green]❌ No files to repack![/bold bright_green]')
        return 0

    console.print(f'  [bold bright_green]📁 Files to repack: {len(edited)}[/bold bright_green]')

    new_files = []
    for e in pak_file._files:
        ne = _cp.copy(e)
        ne.compressed_blocks = [_cp.copy(b) for b in e.compressed_blocks]
        new_files.append(ne)

    old_to_new = {id(pak_file._files[i]): new_files[i] for i in range(len(pak_file._files))}
    edited_paths = {fp: p for fp, (p, _) in edited.items()}

    out_buf = bytearray()

    for dp_str, dir_files in list(all_dirs.items()):
        for name, old_entry in list(dir_files.items()):
            full_path = str(PurePath(dp_str)/name).replace('\\', '/')
            ne = old_to_new.get(id(old_entry), None)
            
            if ne is None:
                ne = _cp.copy(old_entry)
                ne.compressed_blocks = [_cp.copy(b) for b in old_entry.compressed_blocks]
                new_files.append(ne)
                old_to_new[id(old_entry)] = ne

            em = old_entry.encryption_method
            cm = old_entry.compression_method

            if full_path in edited_paths:
                p, template = edited[full_path]
                new_raw = p.read_bytes()
                pak_rel = PurePath(full_path)

                ne.content_hash = SHA1.new(new_raw).digest()
                ne.uncompressed_size = len(new_raw)
                ne.compression_method = template.compression_method if template else cm
                ne.encryption_method = template.encryption_method if template else em
                ne.encrypted = template.encrypted if template else old_entry.encrypted
                ne.unk1 = template.unk1 if template else old_entry.unk1
                
                # FIX 2: If we changed the path of an existing file via target_path, recalculate unk2
                if template and target_path:
                    full_path_str = mp_str + full_path
                    ne.unk2 = SHA1.new(full_path_str.lower().encode('utf-8')).digest()
                else:
                    ne.unk2 = template.unk2 if template else old_entry.unk2
                    
                ne.index_new_sep = template.index_new_sep if template else old_entry.index_new_sep

                if ne.compression_method == CM_NONE:
                    cipher = (_encrypt_plaintext(new_raw, pak_rel, ne.encryption_method)
                              if ne.encrypted else new_raw)
                    ne.offset = len(out_buf)
                    ne.size = len(new_raw)
                    ne.uncompressed_size = len(new_raw)
                    out_buf += cipher
                else:
                    cs = (template.compression_block_size if template and template.compression_block_size > 0 
                          else old_entry.compression_block_size if old_entry.compression_block_size > 0 
                          else 65536)
                    chunks = [new_raw[i:i+cs] for i in range(0, len(new_raw), cs)]
                    new_blks = []
                    for chunk in chunks:
                        compressed = _best_compress(chunk, ne.compression_method, pak_file._zstd_dict)
                        cipher = (_encrypt_plaintext(compressed, pak_rel, ne.encryption_method)
                                  if ne.encrypted else compressed)
                        blk = PakCompressedBlock.__new__(PakCompressedBlock)
                        blk.start = len(out_buf)
                        blk.end = blk.start + len(cipher)
                        out_buf += cipher
                        new_blks.append(blk)

                    ne.compressed_blocks = new_blks
                    ne.offset = new_blks[0].start if new_blks else len(out_buf)
                    ne.size = sum(b.end - b.start for b in new_blks)
                    ne.uncompressed_size = len(new_raw)

                console.print(f'[bright_green]✓ Processed: {full_path}[/bright_green]')

            else:
                if cm == CM_NONE:
                    read_sz = (PakCrypto.align_encrypted_content_size(old_entry.size, em)
                               if old_entry.encrypted else old_entry.size)
                    ne.offset = len(out_buf)
                    out_buf += bytes(orig_fc[old_entry.offset: old_entry.offset + read_sz])

                elif old_entry.compressed_blocks:
                    new_blks = []
                    for ob in old_entry.compressed_blocks:
                        unc = ob.end - ob.start
                        enc = (PakCrypto.align_encrypted_content_size(unc, em)
                               if old_entry.encrypted else unc)
                        nb = PakCompressedBlock.__new__(PakCompressedBlock)
                        nb.start = len(out_buf)
                        nb.end = nb.start + unc
                        out_buf += bytes(orig_fc[ob.start: ob.start + enc])
                        new_blks.append(nb)
                    ne.compressed_blocks = new_blks
                    ne.offset = new_blks[0].start

    if target_path and force_add:
        for fp, (p, template) in edited.items():
            already_processed = False
            for dp_str, dir_files in all_dirs.items():
                for name, entry in dir_files.items():
                    if str(PurePath(dp_str)/name).replace('\\', '/') == fp:
                        already_processed = True
                        break
                if already_processed:
                    break
            
            if not already_processed:
                ne = _cp.copy(template)
                new_raw = p.read_bytes()
                pak_rel = PurePath(fp)
                
                ne.content_hash = SHA1.new(new_raw).digest()
                ne.uncompressed_size = len(new_raw)
                ne.compression_method = template.compression_method
                ne.encryption_method = template.encryption_method
                ne.encrypted = template.encrypted
                ne.unk1 = template.unk1
                
                # FIX 3: Accurately generate the path hash (unk2) for the NEW file
                # The game engine uses this specific SHA1 hash to find the file!
                full_path_str = mp_str + fp
                ne.unk2 = SHA1.new(full_path_str.lower().encode('utf-8')).digest()
                
                ne.index_new_sep = template.index_new_sep

                if ne.compression_method == CM_NONE:
                    cipher = (_encrypt_plaintext(new_raw, pak_rel, ne.encryption_method)
                              if ne.encrypted else new_raw)
                    ne.offset = len(out_buf)
                    ne.size = len(new_raw)
                    ne.uncompressed_size = len(new_raw)
                    out_buf += cipher
                else:
                    cs = template.compression_block_size if template.compression_block_size > 0 else 65536
                    chunks = [new_raw[i:i+cs] for i in range(0, len(new_raw), cs)]
                    new_blks = []
                    for chunk in chunks:
                        compressed = _best_compress(chunk, ne.compression_method, pak_file._zstd_dict)
                        cipher = (_encrypt_plaintext(compressed, pak_rel, ne.encryption_method)
                                  if ne.encrypted else compressed)
                        blk = PakCompressedBlock.__new__(PakCompressedBlock)
                        blk.start = len(out_buf)
                        blk.end = blk.start + len(cipher)
                        out_buf += cipher
                        new_blks.append(blk)

                    ne.compressed_blocks = new_blks
                    ne.offset = new_blks[0].start if new_blks else len(out_buf)
                    ne.size = sum(b.end - b.start for b in new_blks)
                    ne.uncompressed_size = len(new_raw)

                new_files.append(ne)
                
                # FIX 4: Add to all_dirs mapping using the exact validated target_path
                if target_path not in all_dirs:
                    all_dirs[target_path] = {}
                all_dirs[target_path][p.name] = ne
                console.print(f'[bright_green]✓ Added new: {fp}[/bright_green]')

    eidx = {id(new_files[i]): i for i in range(len(new_files))}
    old_id_to_new_idx = {id(pak_file._files[i]): i for i in range(len(pak_file._files))}

    idx = bytearray(_pw_string(mp_str))
    idx += struct.pack('<I', len(new_files))
    for ne in new_files:
        idx += _pw_entry(ne, version)
    idx += struct.pack('<Q', len(all_dirs))
    for dp_str, dir_files in all_dirs.items():
        idx += _pw_string(dp_str)
        idx += struct.pack('<Q', len(dir_files))
        for name, old_e in dir_files.items():
            idx += _pw_string(name)
            # 1) new/injected entries are stored by identity in all_dirs
            found_idx = eidx.get(id(old_e))
            # 2) existing entries -> the rebuilt copy of the original object
            if found_idx is None:
                found_idx = old_id_to_new_idx.get(id(old_e))
            # 3) entries appended mid-loop (never in the original file list)
            if found_idx is None:
                copy_of = next((k for k, v in old_to_new.items() if v is old_e), None)
                if copy_of is not None:
                    found_idx = eidx.get(id(old_to_new[copy_of]))
            if found_idx is None:
                for i, e in enumerate(new_files):
                    if e.offset == old_e.offset and e.size == old_e.size:
                        found_idx = i
                        break
            if found_idx is not None:
                idx += struct.pack('<i', ~found_idx)
            else:
                idx += struct.pack('<i', -1)

    index_plain = bytes(idx)
    new_sha1 = SHA1.new(index_plain).digest()

    if pak_file._pak_info.index_encrypted:
        key = PakCrypto.rsa_extract(pak_file._pak_info.packed_key, RSA_MOD_1)
        iv = PakCrypto.rsa_extract(pak_file._pak_info.packed_iv, RSA_MOD_1)
        aes = AES.new(key, MODE_CBC, iv[:16])
        pad = (-len(index_plain)) % AES.block_size or AES.block_size
        index_bytes = aes.encrypt(index_plain + bytes([pad] * pad))
    else:
        index_bytes = index_plain

    new_idx_offset = len(out_buf)
    new_idx_size = len(index_bytes)
    out_buf += index_bytes

    footer_sz = TencentPakInfo._mem_size(version)
    new_footer = bytearray(orig_fc[-footer_sz:])

    h_key = struct.pack('<5I', *keystream[4:9])
    new_footer[-36:-16] = bytes(a ^ b for a, b in zip(new_sha1, h_key))
    new_footer[-16:-8] = ((new_idx_size ^ (keystream[10] << 32 | keystream[11])).to_bytes(8, 'little'))
    new_footer[-8:] = ((new_idx_offset ^ (keystream[0] << 32 | keystream[1])).to_bytes(8, 'little'))

    out_buf += new_footer

    with open(output_path, 'wb') as f:
        f.write(out_buf)

    return len(edited)


# ==================== MULTI-FILE INJECT + PROTECT (NEW) ====================

def _normalize_dir_key(path_str):
    """'a/b/c' or 'a/b/c/' -> 'a/b/c/'"""
    s = str(path_str).replace('\\', '/').strip('/')
    return (s + '/') if s else ''

def _find_existing_dir(all_dirs, want_dir):
    want = _normalize_dir_key(want_dir).strip('/').lower()
    if not want:
        return ''
    for k in all_dirs:
        if k.strip('/').lower() == want:
            return k
    best = None
    for k in all_dirs:
        key = k.strip('/').lower()
        if key and want.endswith('/' + key):
            if best is None or len(key) > len(best):
                best = k
    return best

def _strip_mount_prefix(pak_file, rel_dir):
    """Strip the pak's mount point from a user-supplied in-pak path."""
    mp = str(pak_file._mount_point).replace('\\', '/').strip('/')
    rd = str(rel_dir).replace('\\', '/').strip('/')
    if mp and (rd.lower() == mp.lower() or rd.lower().startswith(mp.lower() + '/')):
        return rd[len(mp):].lstrip('/')
    return rd

def _pick_template(pak_file, all_dirs, target_dir, file_name):
    ext = Path(file_name).suffix.lower()
    if target_dir in all_dirs:
        for name, e in all_dirs[target_dir].items():
            if Path(name).suffix.lower() == ext:
                return e
    for dp, files in all_dirs.items():
        for name, e in files.items():
            if Path(name).suffix.lower() == ext:
                return e
    for dp, files in all_dirs.items():
        for name, e in files.items():
            return e
    return pak_file._files[0] if pak_file._files else None

def _default_compression(pak_file):
    """Pick the pak's dominant compression method for newly added files."""
    cm_counter = {}
    for e in pak_file._files:
        cm = e.compression_method
        if cm in (CM_ZLIB, CM_ZSTD, CM_ZSTD_DICT):
            cm_counter[cm] = cm_counter.get(cm, 0) + 1
    if pak_file._is_zstd_with_dict and cm_counter.get(CM_ZSTD_DICT, 0):
        return CM_ZSTD_DICT
    if cm_counter.get(CM_ZSTD, 0):
        return CM_ZSTD
    if cm_counter.get(CM_ZSTD_DICT, 0):
        return CM_ZSTD
    return CM_ZLIB

def _write_entry_content(out_buf, ne, plaintext, pak_rel, zstd_dict, fast=False):
    """Encode one entry's plaintext into out_buf (compress + encrypt), updating ne."""
    if ne.compression_method == CM_NONE:
        cipher = (_encrypt_plaintext(plaintext, pak_rel, ne.encryption_method)
                  if ne.encrypted else plaintext)
        ne.offset = len(out_buf)
        ne.size = len(plaintext)
        ne.uncompressed_size = len(plaintext)
        out_buf += cipher
        return
    cs = ne.compression_block_size if ne.compression_block_size > 0 else 65536
    chunks = [plaintext[i:i + cs] for i in range(0, len(plaintext), cs)]
    if not chunks:
        ne.compressed_blocks = []
        ne.offset = len(out_buf)
        ne.size = 0
        ne.uncompressed_size = 0
        return
    n = len(chunks)
    inv = PakCrypto.generate_block_indices(n, ne.encryption_method) if ne.encrypted else list(range(n))
    file_order = [0] * n
    for j in range(n):
        file_order[inv[j]] = j
    new_blks = [None] * n
    for k in range(n):
        chunk = chunks[file_order[k]]
        compressed = _best_compress(chunk, ne.compression_method, zstd_dict, fast=fast)
        cipher = (_encrypt_plaintext(compressed, pak_rel, ne.encryption_method)
                  if ne.encrypted else compressed)
        blk = PakCompressedBlock.__new__(PakCompressedBlock)
        blk.start = len(out_buf)
        blk.end = blk.start + len(cipher)
        out_buf += cipher
        new_blks[k] = blk
    ne.compressed_blocks = new_blks
    ne.offset = new_blks[0].start
    ne.size = sum(b.end - b.start for b in new_blks)
    ne.uncompressed_size = len(plaintext)

def _extract_entry_plaintext(pak_file, entry, full_path):
    em = entry.encryption_method
    cm = entry.compression_method
    path = PurePath(full_path)
    if cm == CM_NONE:
        data = pak_file._peek_content(entry.offset, entry.size, em)
        if entry.encrypted:
            data = PakCrypto.decrypt_block(data, path, em)
        return bytes(data[:entry.uncompressed_size])
    out = bytearray()
    for x in PakCrypto.generate_block_indices(len(entry.compressed_blocks), em):
        data = pak_file._peek_block_content(entry.compressed_blocks[x], em)
        if entry.encrypted:
            data = PakCrypto.decrypt_block(data, path, em)
        out += PakCompression.decompress_block(data, pak_file._zstd_dict, cm)
    return bytes(out)

def _copy_original_content(out_buf, pak_file, ne, old_entry):
    """Copy an un-modified entry's content into out_buf, rewriting offsets."""
    em = old_entry.encryption_method
    if old_entry.compression_method == CM_NONE:
        read_sz = (PakCrypto.align_encrypted_content_size(old_entry.size, em)
                   if old_entry.encrypted else old_entry.size)
        ne.offset = len(out_buf)
        out_buf += bytes(pak_file._file_content[old_entry.offset: old_entry.offset + read_sz])
    elif old_entry.compressed_blocks:
        new_blks = []
        for ob in old_entry.compressed_blocks:
            unc = ob.end - ob.start
            enc = (PakCrypto.align_encrypted_content_size(unc, em)
                   if old_entry.encrypted else unc)
            nb = PakCompressedBlock.__new__(PakCompressedBlock)
            nb.start = len(out_buf)
            nb.end = nb.start + unc
            out_buf += bytes(pak_file._file_content[ob.start: ob.start + enc])
            new_blks.append(nb)
        ne.compressed_blocks = new_blks
        ne.offset = new_blks[0].start
    ne.encryption_method = old_entry.encryption_method
    ne.encrypted = old_entry.encrypted

def _write_pak_index_footer(pak_file, mp_str, all_dirs, new_files, old_to_new, out_buf, output_path):
    """Write index + footer for a rebuilt pak (correct identity-based mapping)."""
    version = pak_file._pak_info.version
    keystream = PakCrypto.zuc_keystream()
    eidx = {id(new_files[i]): i for i in range(len(new_files))}
    old_id_to_new_idx = {id(pak_file._files[i]): i for i in range(len(pak_file._files))}
    idx = bytearray(_pw_string(mp_str))
    idx += struct.pack('<I', len(new_files))
    for ne in new_files:
        idx += _pw_entry(ne, version)
    idx += struct.pack('<Q', len(all_dirs))
    for dp_str, dir_files in all_dirs.items():
        idx += _pw_string(dp_str)
        idx += struct.pack('<Q', len(dir_files))
        for name, old_e in dir_files.items():
            idx += _pw_string(name)
            found_idx = eidx.get(id(old_e))
            if found_idx is None:
                found_idx = old_id_to_new_idx.get(id(old_e))
            if found_idx is None:
                copy_of = next((k for k, v in old_to_new.items() if v is old_e), None)
                if copy_of is not None:
                    found_idx = eidx.get(id(old_to_new[copy_of]))
            if found_idx is None:
                for i, e in enumerate(new_files):
                    if e.offset == old_e.offset and e.size == old_e.size:
                        found_idx = i
                        break
            idx += struct.pack('<i', ~found_idx if found_idx is not None else -1)
    index_plain = bytes(idx)
    new_sha1 = SHA1.new(index_plain).digest()
    if pak_file._pak_info.index_encrypted:
        key = PakCrypto.rsa_extract(pak_file._pak_info.packed_key, RSA_MOD_1)
        iv = PakCrypto.rsa_extract(pak_file._pak_info.packed_iv, RSA_MOD_1)
        aes = AES.new(key, MODE_CBC, iv[:16])
        pad = (-len(index_plain)) % AES.block_size or AES.block_size
        index_bytes = aes.encrypt(index_plain + bytes([pad] * pad))
    else:
        index_bytes = index_plain
    new_idx_offset = len(out_buf)
    new_idx_size = len(index_bytes)
    out_buf += index_bytes
    footer_sz = TencentPakInfo._mem_size(version)
    new_footer = bytearray(pak_file._file_content[-footer_sz:])
    h_key = struct.pack('<5I', *keystream[4:9])
    new_footer[-36:-16] = bytes(a ^ b for a, b in zip(new_sha1, h_key))
    new_footer[-16:-8] = ((new_idx_size ^ (keystream[10] << 32 | keystream[11])).to_bytes(8, 'little'))
    new_footer[-8:] = ((new_idx_offset ^ (keystream[0] << 32 | keystream[1])).to_bytes(8, 'little'))
    out_buf += new_footer
    with open(output_path, 'wb') as f:
        f.write(out_buf)

def inject_edit_files(pak_file, edit_root, output_path, protect_new=False, sm4_type=47):
    """Inject/edit MULTIPLE files from edit_root into the pak.

    Each file's relative path inside edit_root is preserved as its path inside
    the pak (mount point excluded). Existing entries are replaced (any size),
    new entries are added. Optionally encrypt injected files with game-native
    SM4 so they are never stored in plaintext.
    """
    import copy as _cp
    version = pak_file._pak_info.version
    if version < 12:
        raise ValueError(f'Unsupported pak version: {version} (need >= 12)')

    edit_files = [p for p in Path(edit_root).rglob('*') if p.is_file()]
    if not edit_files:
        raise ValueError(f'No files found in EDIT folder: {edit_root}')

    mp_str, all_dirs = _get_all_dirs_and_mp(pak_file)

    injections = {}
    for p in edit_files:
        rel = p.relative_to(edit_root)
        parts = rel.parts
        file_name = parts[-1]
        rel_dir = '/'.join(parts[:-1]).replace('\\', '/')
        rel_dir = _strip_mount_prefix(pak_file, rel_dir)
        target_dir = _find_existing_dir(all_dirs, rel_dir) if rel_dir.strip('/') else ''
        if target_dir is None:
            target_dir = _normalize_dir_key(rel_dir)
        existing = None
        if target_dir in all_dirs:
            for name, e in list(all_dirs[target_dir].items()):
                if name.lower() == file_name.lower():
                    existing = (name, e)
                    break
        if existing:
            full_path = target_dir + existing[0]
            injections[full_path] = (p, existing[1], False)
        else:
            full_path = target_dir + file_name
            template = _pick_template(pak_file, all_dirs, target_dir, file_name)
            injections[full_path] = (p, template, True)
        console.print(f'  [bold bright_green]●[/bold bright_green] [bright_green]{full_path}[/bright_green] '
                      f'[dim]({"replace existing" if existing else "add new"})[/dim]')

    new_files = []
    for e in pak_file._files:
        ne = _cp.copy(e)
        ne.compressed_blocks = [_cp.copy(b) for b in e.compressed_blocks]
        new_files.append(ne)
    old_to_new = {id(pak_file._files[i]): new_files[i] for i in range(len(pak_file._files))}

    out_buf = bytearray()
    edited_count = 0
    new_count = 0

    for dp_str, dir_files in list(all_dirs.items()):
        for name, old_entry in list(dir_files.items()):
            full_path = str(PurePath(dp_str) / name).replace('\\', '/')
            ne = old_to_new.get(id(old_entry), None)
            if ne is None:
                ne = _cp.copy(old_entry)
                ne.compressed_blocks = [_cp.copy(b) for b in old_entry.compressed_blocks]
                new_files.append(ne)
                old_to_new[id(old_entry)] = ne

            if full_path in injections:
                p, template, is_new = injections[full_path]
                new_raw = p.read_bytes()
                pak_rel = PurePath(full_path)
                ne.content_hash = SHA1.new(new_raw).digest()
                ne.uncompressed_size = len(new_raw)
                if is_new:
                    ne.compression_method = _default_compression(pak_file)
                    if protect_new:
                        ne.encryption_method = sm4_type
                        ne.encrypted = True
                    else:
                        ne.encryption_method = template.encryption_method if template else 0
                        ne.encrypted = template.encrypted if template else False
                    ne.unk1 = template.unk1 if template else 0
                    ne.compression_block_size = (template.compression_block_size if template
                                                 and template.compression_block_size > 0 else 65536)
                    ne.index_new_sep = template.index_new_sep if template else 0
                    new_count += 1
                else:
                    ne.compression_method = old_entry.compression_method
                    if protect_new:
                        ne.encryption_method = sm4_type
                        ne.encrypted = True
                    else:
                        ne.encryption_method = old_entry.encryption_method
                        ne.encrypted = old_entry.encrypted
                    ne.unk1 = old_entry.unk1
                    ne.compression_block_size = (old_entry.compression_block_size
                                                 if old_entry.compression_block_size > 0 else 65536)
                    ne.index_new_sep = old_entry.index_new_sep
                    edited_count += 1
                ne.unk2 = SHA1.new((mp_str + full_path).lower().encode('utf-8')).digest()
                _write_entry_content(out_buf, ne, new_raw, pak_rel, pak_file._zstd_dict)
                console.print(f'  [bold #00FF88]✓[/bold #00FF88] '
                              f'[bright_green]{"Edited" if not is_new else "Added"}[/bright_green]: {full_path} '
                              f'[dim]({len(new_raw):,} bytes)[/dim]')
            else:
                _copy_original_content(out_buf, pak_file, ne, old_entry)

    # add brand-new files that were not in the original index
    for full_path, (p, template, is_new) in injections.items():
        if not is_new:
            continue
        already = False
        for dp_str, dir_files in all_dirs.items():
            for name, entry in dir_files.items():
                if str(PurePath(dp_str) / name).replace('\\', '/') == full_path:
                    already = True
                    break
            if already:
                break
        if already:
            continue
        ne = _cp.copy(template) if template else None
        if ne is None:
            ne = TencentPakEntry(Reader(b''), version)
            ne.compression_method = CM_NONE
            ne.encrypted = False
        else:
            ne.compressed_blocks = [_cp.copy(b) for b in template.compressed_blocks]
        new_raw = p.read_bytes()
        pak_rel = PurePath(full_path)
        ne.content_hash = SHA1.new(new_raw).digest()
        ne.uncompressed_size = len(new_raw)
        ne.compression_method = _default_compression(pak_file)
        if protect_new:
            ne.encryption_method = sm4_type
            ne.encrypted = True
        else:
            ne.encryption_method = template.encryption_method if template else 0
            ne.encrypted = template.encrypted if template else False
        ne.unk1 = template.unk1 if template else 0
        ne.compression_block_size = (template.compression_block_size if template
                                     and template.compression_block_size > 0 else 65536)
        ne.index_new_sep = template.index_new_sep if template else 0
        ne.unk2 = SHA1.new((mp_str + full_path).lower().encode('utf-8')).digest()
        _write_entry_content(out_buf, ne, new_raw, pak_rel, pak_file._zstd_dict)
        new_files.append(ne)
        old_to_new[id(ne)] = ne
        dp_key = full_path.rsplit('/', 1)[0] + '/' if '/' in full_path else ''
        all_dirs.setdefault(dp_key, {})[full_path.rsplit('/', 1)[-1]] = ne
        new_count += 1
        console.print(f'  [bold #00FF88]✓[/bold #00FF88] '
                      f'[bright_green]Added[/bright_green]: {full_path} '
                      f'[dim]({len(new_raw):,} bytes)[/dim]')

    _write_pak_index_footer(pak_file, mp_str, all_dirs, new_files, old_to_new, out_buf, output_path)
    return edited_count, new_count

def protect_pak_file(pak_file, output_path, sm4_type=47):
    """Re-encrypt every entry with game-native SM4 and rebuild the pak.

    No plaintext remains: generic unpackers cannot read the content while the
    game still decrypts it normally (SM4 types are the game's own methods).
    """
    import copy as _cp
    version = pak_file._pak_info.version
    if version < 12:
        raise ValueError(f'Unsupported pak version: {version} (need >= 12)')

    mp_str, all_dirs = _get_all_dirs_and_mp(pak_file)
    new_files = []
    for e in pak_file._files:
        ne = _cp.copy(e)
        ne.compressed_blocks = [_cp.copy(b) for b in e.compressed_blocks]
        new_files.append(ne)
    old_to_new = {id(pak_file._files[i]): new_files[i] for i in range(len(pak_file._files))}

    out_buf = bytearray()
    protected = 0
    skipped = 0

    for dp_str, dir_files in list(all_dirs.items()):
        for name, old_entry in list(dir_files.items()):
            full_path = str(PurePath(dp_str) / name).replace('\\', '/')
            ne = old_to_new.get(id(old_entry), None)
            if ne is None:
                ne = _cp.copy(old_entry)
                ne.compressed_blocks = [_cp.copy(b) for b in old_entry.compressed_blocks]
                new_files.append(ne)
                old_to_new[id(old_entry)] = ne

            is_marker = (old_entry.compression_method == CM_NONE and old_entry.size == 0)
            is_zdict = (pak_file._zstd_dict_entry is not None and old_entry is pak_file._zstd_dict_entry)
            if is_marker or is_zdict:
                _copy_original_content(out_buf, pak_file, ne, old_entry)
                skipped += 1
                continue

            try:
                plaintext = _extract_entry_plaintext(pak_file, old_entry, full_path)
            except Exception:
                _copy_original_content(out_buf, pak_file, ne, old_entry)
                skipped += 1
                console.print(f"  [bold bright_green]![/bold bright_green] [bright_green]Skipped undecryptable[/bright_green]: {full_path}")
                continue
            ne.compression_method = old_entry.compression_method
            if ne.compression_method == CM_NONE:
                ne.compression_method = CM_ZLIB
            ne.encryption_method = sm4_type
            ne.encrypted = True
            ne.unk1 = old_entry.unk1
            ne.unk2 = old_entry.unk2
            ne.index_new_sep = old_entry.index_new_sep
            ne.compression_block_size = (old_entry.compression_block_size
                                         if old_entry.compression_block_size > 0 else 65536)
            _write_entry_content(out_buf, ne, plaintext, PurePath(full_path), pak_file._zstd_dict, fast=True)
            protected += 1
            if protected <= 12 or protected % 250 == 0:
                console.print(f'  [bold #FF00FF]🔒[/bold #FF00FF] '
                              f'[green]Re-encrypted[/green]: {full_path} '
                              f'[dim]({len(plaintext):,} bytes)[/dim]')

    _write_pak_index_footer(pak_file, mp_str, all_dirs, new_files, old_to_new, out_buf, output_path)
    return protected, skipped


# ==================== ORIGINAL REPACK (For Option 2) ====================

def _repack_compressed_with_display(outfh, pak_file, entry, pak_relative_path, new_data, repack_dir, display):
    """Original compressed repack with display - Working fine"""
    blocks = entry.compressed_blocks
    enc_method = entry.encryption_method
    comp_method = entry.compression_method
    order = PakCrypto.generate_block_indices(len(blocks), enc_method)
    
    if len(new_data) != entry.uncompressed_size:
        if len(new_data) < entry.uncompressed_size:
            new_data = new_data.ljust(entry.uncompressed_size, b'\x00')
        else:
            new_data = new_data[:entry.uncompressed_size]

    if len(blocks) > 1:
        if entry.compression_block_size > 0:
            chunk_size = entry.compression_block_size
        else:
            block_sizes = [blk.end - blk.start for blk in blocks]
            total_block_size = sum(block_sizes)
            avg_block_size = total_block_size / len(blocks)
            avg_compression_ratio = total_block_size / entry.uncompressed_size if entry.uncompressed_size > 0 else 1
            chunk_size = int(avg_block_size / avg_compression_ratio) if avg_compression_ratio > 0 else 65536
        
        ptr = 0
        for logical_i, phys_i in enumerate(order):
            blk = blocks[phys_i]
            target_size = blk.end - blk.start
            chunk_len = min(chunk_size, len(new_data) - ptr)
            if chunk_len <= 0: break
            chunk = new_data[ptr:ptr + chunk_len]
            ptr += chunk_len
            
            with open(pak_file._file_path, 'rb') as src:
                src.seek(blk.start)
                original_compressed = src.read(target_size)
            
            compressed_ok = False
            new_compressed = None
            zstd_dict = pak_file._zstd_dict if comp_method == CM_ZSTD_DICT else None
            
            if comp_method in (CM_ZSTD, CM_ZSTD_DICT):
                for level in [22, 19, 16, 13, 10, 7, 4, 1]:
                    c = ZstdCompressor(level=level, dict_data=zstd_dict, threads=1)
                    new_compressed = c.compress(chunk)
                    if len(new_compressed) <= target_size:
                        compressed_ok = True
                        break
            elif comp_method == CM_ZLIB:
                new_compressed = zlib.compress(chunk, zlib.Z_BEST_COMPRESSION)
                if len(new_compressed) <= target_size:
                    compressed_ok = True
            
            if not compressed_ok:
                outfh.seek(blk.start)
                outfh.write(original_compressed)
                display.add_block(logical_i, target_size, False)
                continue
            
            if entry.encrypted:
                if PakCrypto._is_sm4_method(enc_method):
                    pad_len = -len(new_compressed) % 16
                    if pad_len > 0: new_compressed += b'\x00' * pad_len
                new_compressed = _encrypt_plaintext(new_compressed, pak_relative_path, enc_method)
            
            if len(new_compressed) > target_size:
                outfh.seek(blk.start)
                outfh.write(original_compressed)
                display.add_block(logical_i, target_size, False)
            else:
                outfh.seek(blk.start)
                outfh.write(new_compressed)
                if len(new_compressed) < target_size:
                    outfh.write(b'\x00' * (target_size - len(new_compressed)))
                ratio = len(new_compressed) / len(chunk) if len(chunk) > 0 else 1
                display.add_block(logical_i, target_size, True, ratio)
    else:
        if not blocks: return
        blk = blocks[0]
        target_size = blk.end - blk.start
        
        with open(pak_file._file_path, 'rb') as src:
            src.seek(blk.start)
            original_compressed = src.read(target_size)
        
        compressed_ok = False
        new_compressed = None
        zstd_dict = pak_file._zstd_dict if comp_method == CM_ZSTD_DICT else None
        
        if comp_method in (CM_ZSTD, CM_ZSTD_DICT):
            for level in [22, 19, 16, 13, 10, 7, 4, 1]:
                c = ZstdCompressor(level=level, dict_data=zstd_dict, threads=1)
                new_compressed = c.compress(new_data)
                if len(new_compressed) <= target_size:
                    compressed_ok = True
                    break
        elif comp_method == CM_ZLIB:
            new_compressed = zlib.compress(new_data, zlib.Z_BEST_COMPRESSION)
            if len(new_compressed) <= target_size:
                compressed_ok = True
        
        if not compressed_ok:
            outfh.seek(blk.start)
            outfh.write(original_compressed)
            display.add_block(0, target_size, False)
            return
        
        if entry.encrypted:
            if PakCrypto._is_sm4_method(enc_method):
                pad_len = -len(new_compressed) % 16
                if pad_len > 0: new_compressed += b'\x00' * pad_len
            new_compressed = _encrypt_plaintext(new_compressed, pak_relative_path, enc_method)
        
        if len(new_compressed) > target_size:
            outfh.seek(blk.start)
            outfh.write(original_compressed)
            display.add_block(0, target_size, False)
        else:
            outfh.seek(blk.start)
            outfh.write(new_compressed)
            if len(new_compressed) < target_size:
                outfh.write(b'\x00' * (target_size - len(new_compressed)))
            ratio = len(new_compressed) / len(new_data) if len(new_data) > 0 else 1
            display.add_block(0, target_size, True, ratio)

def smart_resolve_by_fingerprint(filename: str, repack_file: Path, candidates: list):
    repack_size = repack_file.stat().st_size
    size_matches = [(path, entry) for path, entry in candidates if entry.uncompressed_size == repack_size]
    if len(size_matches) == 1:
        return size_matches[0]
    if not size_matches:
        return None
    def fingerprint(e):
        return (e.uncompressed_size, e.size, e.compression_method, len(e.compressed_blocks), e.compression_block_size)
    base_fp = fingerprint(size_matches[0][1])
    final_matches = [(path, entry) for path, entry in size_matches if fingerprint(entry) == base_fp]
    if len(final_matches) == 1:
        return final_matches[0]
    return None

def repack_pak_file_with_block_display(pak_file, edited_root: Path, output_path: Path):
    """Original repack with simple block display - WORKING"""
    shutil.copy2(pak_file._file_path, output_path)
    
    pak_name_map = {}
    for dir_path, files in pak_file._index.items():
        for name, entry in files.items():
            full_path = str(PurePath(dir_path) / name).replace('\\', '/')
            key = name.lower()
            pak_name_map.setdefault(key, []).append((full_path, entry))
    
    edited = {}
    for p in edited_root.rglob('*'):
        if not p.is_file():
            continue
        fname_lower = p.name.lower()
        if fname_lower in pak_name_map:
            candidates = pak_name_map[fname_lower]
            if len(candidates) == 1:
                full_path, entry = candidates[0]
                edited[full_path] = (p, entry)
            else:
                resolved = smart_resolve_by_fingerprint(filename=p.name, repack_file=p, candidates=candidates)
                if resolved:
                    full_path, entry = resolved
                    edited[full_path] = (p, entry)
        else:
            stem = p.stem.lower()
            ext = p.suffix.lower()
            for dir_path, files in pak_file._index.items():
                for name, entry in files.items():
                    if Path(name).stem.lower() == stem and Path(name).suffix.lower() == ext:
                        full_path = str(PurePath(dir_path) / name).replace('\\', '/')
                        edited[full_path] = (p, entry)
                        break
    
    if not edited:
        console.print('[bold #FF0055]❌ No files to repack![/bold #FF0055]')
        return
    
    total_files = len(edited)
    display = SimpleBlockDisplay(total_files, pak_file._file_path.name)
    
    with open(output_path, 'r+b') as outfh:
        for full_path, (p, entry) in edited.items():
            file_name = p.name
            total_blocks = len(entry.compressed_blocks) if entry.compressed_blocks else 1
            
            display.start_file(file_name, total_blocks)
            new_data = p.read_bytes()
            pak_rel = PurePath(full_path)
            
            if entry.compression_method == CM_NONE:
                _repack_uncompressed(outfh, pak_file, entry, pak_rel, new_data)
                display.add_block(0, len(new_data), True)
            else:
                _repack_compressed_with_display(outfh, pak_file, entry, pak_rel, new_data, edited_root, display)
            
            display.finish_file()
    
    display.final_summary()

def detect_repack_mode(pak_path: Path) -> str:
    name = pak_path.name.lower()
    if name == 'mini_obb.pak':
        return 'MINI_OBB'
    if 'zsdic' in name:
        return 'OBBZSDIC'
    if 'game' in name or 'patch' in name:
        return 'GAMEPATCH'
    return 'OBBZSDIC'

def repack_mini_obb(pak, repack_dir, output_pak):
    console.print('[bold #00FFFF]🧩 Repack Mode: MINI_OBB[/bold #00FFFF]')
    pak._is_zstd_with_dict = False
    pak._zstd_dict = None
    repack_pak_file_with_block_display(pak_file=pak, edited_root=repack_dir, output_path=output_pak)

def repack_obbzsdic(pak, repack_dir, output_pak):
    console.print('[bold #00FFFF]🧩 Repack Mode: OBBZSDIC[/bold #00FFFF]')
    repack_pak_file_with_block_display(pak_file=pak, edited_root=repack_dir, output_path=output_pak)

def repack_gamepatch(pak, repack_dir, output_pak):
    console.print('[bold #00FFFF]🧩 Repack Mode: GAMEPATCH[/bold #00FFFF]')
    pak._is_zstd_with_dict = False
    pak._zstd_dict = None
    repack_pak_file_with_block_display(pak_file=pak, edited_root=repack_dir, output_path=output_pak)

def ensure_directories(base_dir: Path):
    (base_dir / "PAK").mkdir(parents=True, exist_ok=True)
    (base_dir / "UNPACK").mkdir(parents=True, exist_ok=True)
    (base_dir / "REPACK").mkdir(parents=True, exist_ok=True)
    (base_dir / "RESULT").mkdir(parents=True, exist_ok=True)
    (base_dir / "EXE").mkdir(parents=True, exist_ok=True)
    # New directories for PAK TOOL (Options 3 & 4)
    pak_tool_dir = base_dir / "PAK TOOL"
    (pak_tool_dir / "EDIT").mkdir(parents=True, exist_ok=True)
    (pak_tool_dir / "UNPACK").mkdir(parents=True, exist_ok=True)
    (pak_tool_dir / "RESULT").mkdir(parents=True, exist_ok=True)
    (pak_tool_dir / "PAK").mkdir(parents=True, exist_ok=True)
    # LUA TOOL (menu 7)
    for _d in ("Lua_org", "Lua_Decript", "EDIT_LUA", "Lua_Rueslt"):
        (base_dir / "LUA TOOL" / _d).mkdir(parents=True, exist_ok=True)


def load_index_csv(csv_path: Path) -> List[str]:
    if not csv_path.exists():
        return []
    out = []
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            s = line.strip().replace('\\', '/').lstrip('/')
            if s:
                out.append(s)
    return out

def find_index_for_pak(data_path: Path, pakname: str) -> Optional[Path]:
    # 1) Global TOOL/EXE/index.csv (user ready-made, valid for all)
    c0 = data_path / "EXE" / "index.csv"
    if c0.exists() and c0.stat().st_size > 0:
        return c0
    # 2) Per-pak UNPACK/{pakname}/index.csv (written on unpack)
    c1 = data_path / "UNPACK" / pakname / "index.csv"
    if c1.exists() and c1.stat().st_size > 0:
        return c1
    # 3) Per-pak EXE/index_{pakname}.csv
    c2 = data_path / "EXE" / f"index_{pakname}.csv"
    if c2.exists() and c2.stat().st_size > 0:
        return c2
    # 4) Fallback: PAKTOOL_NEW global index (same device convenience)
    try:
        fb = Path("/data/data/com.termux/files/home/PAKTOOL_NEW/EXE/index.csv")
        if fb.exists() and fb.stat().st_size > 0:
            return fb
    except Exception:
        pass
    return None

def build_fullpath_entry_map(pak_file) -> Dict[str, Any]:
    m = {}
    for dir_path, files in pak_file._index.items():
        for name, entry in files.items():
            full = str(PurePath(dir_path) / name).replace("\\", "/").lstrip("/")
            # skip mount '.' prefix artefacts
            if full.startswith("./"):
                full = full[2:]
            m[full] = entry
    return m

def write_pack_index_csv(pak_file, csv_path: Path) -> int:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    paths = sorted(set(build_fullpath_entry_map(pak_file).keys()))
    with open(csv_path, 'w', encoding='utf-8') as f:
        for p in paths:
            f.write(p + "\n")
    return len(paths)

def ensure_exe_index(data_path: Path, pak_file=None, pakname: str = "") -> Optional[Path]:
    """Make sure TOOL/EXE/index.csv exists. Copy from PAKTOOL_NEW if possible, else generate."""
    exe = data_path / "EXE" / "index.csv"
    if exe.exists() and exe.stat().st_size > 0:
        return exe
    # Try copy from PAKTOOL_NEW (user already has 163k ready-made index)
    try:
        src = Path("/data/data/com.termux/files/home/PAKTOOL_NEW/EXE/index.csv")
        if src.exists() and src.stat().st_size > 0:
            (data_path / "EXE").mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, exe)
            console.print(f"[dim]📄 EXE/index.csv copied from PAKTOOL_NEW ({exe})[/dim]")
            return exe
    except Exception:
        pass
    # Generate from current pak
    if pak_file is not None:
        n = write_pack_index_csv(pak_file, exe)
        console.print(f"[dim]📄 EXE/index.csv generated ({n} paths)[/dim]")
        return exe
    return None

def detect_unpacked_paks(data_path: Path) -> List[Path]:
    root = data_path / "UNPACK"
    if not root.exists():
        return []
    return sorted([p for p in root.iterdir() if p.is_dir()], key=lambda x: x.name.lower())

def find_original_pak_for_unpack(data_path: Path, pakname: str) -> Optional[Path]:
    # Search PAK/, PAK TOOL/PAK/, RESULT/ (case-insensitive stem match)
    search_dirs = [data_path / "PAK", data_path / "PAK TOOL" / "PAK", data_path / "RESULT"]
    for d in search_dirs:
        if not d.exists():
            continue
        exact = d / f"{pakname}.pak"
        if exact.exists():
            return exact
        for p in d.glob("*.pak"):
            if p.stem.lower() == pakname.lower():
                return p
    return None

def do_repack_from_unpack(data_path: Path, unpack_entry: Path, force_target_path: Optional[str] = None) -> None:
    """Repack UNPACK/{pakname}/edited/ -> RESULT/{pak}.pak
    Modes: 1 folder-wise, 2 index.csv auto. force_target_path = manual TO-PATH mode.
    """
    pakname = unpack_entry.name
    edited_dir = unpack_entry / "edited"
    if not edited_dir.exists():
        edited_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[bright_green]⚠ Created edited/: UNPACK/{pakname}/edited/ — put your edited files there first.[/bright_green]")
        return
    files = [f for f in edited_dir.rglob("*") if f.is_file() and f.name not in SKIP_NAMES and not f.name.startswith("Debug_")]
    if not files:
        console.print("[bold bright_green]❌ edited/ folder is empty![/bold bright_green]")
        console.print(f"[bright_green]📁 Put files in: UNPACK/{pakname}/edited/[/bright_green]")
        console.print("[dim]2 ways: (1) folder-wise path, (2) file only + index.csv auto-match[/dim]")
        console.print("[dim]Folder-wise ex: UNPACK/{}/edited/Content/Lua/GameLua/Mod/BRMod/Gameplay/Core/BRPlayerCharacterBase.lua[/dim]".format(pakname))
        console.print("[dim]index.csv ex: just drop BRPlayerCharacterBase.lua in edited/, path auto from EXE/index.csv[/dim]")
        return
    orig_pak = find_original_pak_for_unpack(data_path, pakname)
    if orig_pak is None or not orig_pak.exists():
        console.print(f"[bold bright_green]❌ Original PAK not found for '{pakname}'![/bold bright_green]")
        console.print(f"[bright_green]📁 Put original .pak in: TOOL/PAK/{pakname}.pak  (or PAK TOOL/PAK/)[/bright_green]")
        return
    console.print(Panel(
        f"[bright_green]PAK     :[/] [bright_green]{orig_pak.name}[/bright_green]\n"
        f"[bright_green]Edited  :[/] [bright_green]{len(files)} file(s)[/bright_green] [dim](UNPACK/{pakname}/edited/)[/dim]",
        title="🔧 REPACK", border_style="green", padding=(0, 2)))
    mode = "1"
    target_path_manual = force_target_path
    if force_target_path is None:
        console.print("[bold bright_green]Edited file ka path kaise resolve karu?[/bold bright_green]")
        console.print("  [bold bright_green][1][/] Folder-wise — edited/ me full path folders bane hai")
        console.print("      [dim]ex: UNPACK/{}/edited/Content/Lua/.../file.lua[/dim]".format(pakname))
        console.print("  [bold bright_green][2][/] index.csv se auto — sirf file edited/ me daalo, path EXE/index.csv se")
        console.print("      [dim]ex: UNPACK/{}/edited/file.lua  +  EXE/index.csv[/dim]".format(pakname))
        mode = safe_input("Select (1/2): ").strip()
        if mode not in ("1", "2"):
            console.print("[bright_green]❌ Invalid — choose 1 or 2.[/bright_green]")
            return
    else:
        mode = "1"
    try:
        console.print("[bright_green]📦 Loading PAK...[/bright_green]")
        pak = TencentPakFile(orig_pak)
        fmap = build_fullpath_entry_map(pak)
        lower_map = {k.lower(): (k, v) for k, v in fmap.items()}
        name_map: Dict[str, list] = {}
        for full, entry in fmap.items():
            name_map.setdefault(Path(full).name.lower(), []).append((full, entry))
        index_paths: List[str] = []
        index_name_map: Dict[str, list] = {}
        if mode == "2":
            idx = find_index_for_pak(data_path, pakname)
            if idx is None:
                # try to create from current pak
                ensure_exe_index(data_path, pak, pakname)
                idx = find_index_for_pak(data_path, pakname)
            if idx is None:
                console.print("[bold bright_green]❌ EXE/index.csv not found![/bold bright_green]")
                console.print("[bright_green]📁 Put ready-made index.csv at: TOOL/EXE/index.csv[/bright_green]")
                console.print("[dim]index.csv lines ex: ShadowTrackerExtra/Content/Lua/.../file.lua[/dim]")
                return
            index_paths = load_index_csv(idx)
            console.print(f"[bright_green]📄 index.csv loaded: {idx} ({len(index_paths)} paths)[/bright_green]")
            for p in index_paths:
                index_name_map.setdefault(Path(p).name.lower(), []).append(p)
        # Manual TO-PATH: validate target dir
        manual_dir_key = None
        if target_path_manual is not None:
            target_path_manual = target_path_manual.replace('\\', '/').strip('/')
            mp_str_tmp, all_dirs_tmp = _get_all_dirs_and_mp(pak)
            matched = None
            for k in all_dirs_tmp.keys():
                if k.strip('/').lower() == target_path_manual.lower():
                    matched = k
                    break
            manual_dir_key = matched if matched else (target_path_manual.strip('/') + '/')
            console.print(f"[bright_green]🎯 Target path: {manual_dir_key}[/bright_green]")
        RESULT_DIR = data_path / "RESULT"
        RESULT_DIR.mkdir(parents=True, exist_ok=True)
        output_pak = RESULT_DIR / orig_pak.name
        resolved = {}
        skipped = []
        for f in files:
            target_full: Optional[str] = None
            entry = None
            if target_path_manual is not None:
                # All files go into manual target dir (by filename)
                want = manual_dir_key + f.name
                hit = lower_map.get(want.lower())
                if hit is None:
                    hit = lower_map.get(_strip_mount_prefix(pak, want).lower())
                if hit:
                    target_full, entry = hit
                else:
                    # New file to manual path — need template for rebuild
                    # Use any same-ext entry as template
                    tmpl = None
                    for _full, _e in fmap.items():
                        if Path(_full).suffix.lower() == f.suffix.lower():
                            tmpl = _e
                            break
                    if tmpl is None:
                        tmpl = next(iter(fmap.values()))
                    target_full, entry = want, tmpl
            elif mode == "1":
                rel = str(f.relative_to(edited_dir)).replace("\\", "/").lstrip("/")
                hit = lower_map.get(rel.lower())
                if hit is None:
                    hit = lower_map.get(_strip_mount_prefix(pak, rel).lower())
                if hit:
                    target_full, entry = hit
                else:
                    skipped.append(f"{f.name} (path not found: {rel})")
                    console.print(f"[bright_green]✗ No match: {rel}[/bright_green]")
                    console.print(f"[dim]  Hint: folder-wise me exact in-pak path rakho, ya mode 2 (index.csv) use karo[/dim]")
                    continue
            else:
                key = f.name.lower()
                cands = name_map.get(key, [])
                if len(cands) == 1:
                    target_full, entry = cands[0]
                elif len(cands) > 1:
                    match_resolved = smart_resolve_by_fingerprint(f.name, f, cands)
                    if match_resolved:
                        target_full, entry = match_resolved
                    else:
                        skipped.append(f"{f.name} (multiple matches, size unclear)")
                        console.print(f"[bright_green]⚠ Multiple matches for {f.name}:[/bright_green]")
                        for fp, _ in cands[:8]:
                            console.print(f"    - {fp}")
                        continue
                else:
                    idx_hits = index_name_map.get(key, []) if index_paths else []
                    found = None
                    for ip in idx_hits:
                        hit = lower_map.get(ip.lower())
                        if hit is None:
                            hit = lower_map.get(_strip_mount_prefix(pak, ip).lower())
                        if hit:
                            found = hit
                            break
                    if found:
                        target_full, entry = found
                    else:
                        skipped.append(f"{f.name} (name not found in index.csv)")
                        console.print(f"[bright_green]✗ Not found in index.csv: {f.name}[/bright_green]")
                        continue
            if entry is not None and getattr(entry, 'encryption_method', 0) == EM_UNKNOWN_17:
                skipped.append(f"{f.name} (ENC 17 unsupported)")
                console.print(f"[bold bright_green]⚠ SKIPPED {target_full}: ENC 17 cipher unknown — cannot repack safely.[/bold bright_green]")
                continue
            resolved[target_full] = f
        if not resolved:
            console.print("[bold bright_green]❌ Nothing to repack (all skipped)![/bold bright_green]")
            return
        tmpdir = Path(tempfile.mkdtemp(prefix="toolrepack_"))
        try:
            for target_full, disk in resolved.items():
                dest = tmpdir / target_full
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(disk, dest)
            if target_path_manual is not None:
                # force_add new files to manual path
                count = repack_pak_file_full(pak, tmpdir, output_pak, target_path_manual, force_add=True)
                done_msg = f"{count} file(s) -> {target_path_manual}"
            else:
                edited_n, added_n = inject_edit_files(pak, tmpdir, output_pak, protect_new=False)
                done_msg = f"{edited_n} replaced" + (f", {added_n} added" if added_n else "")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        console.print(Panel(
            f"[bold bright_green]✅ REPACK COMPLETE — {done_msg}[/bold bright_green]\n"
            f"[bright_green]Output:[/] [bright_green]RESULT/{output_pak.name}[/bright_green] [dim](any size allowed — full rebuild)[/dim]\n"
            f"[bright_green]Skipped:[/] {len(skipped)}" +
            ("".join(f"\n  - {s}" for s in skipped[:10]) if skipped else ""),
            title="✅ SUCCESS", border_style="bright_green", padding=(1, 2)))
    except Exception as e:
        console.print(f"[bold bright_green]❌ Repack failed: {e}[/bold bright_green]")
        import traceback
        traceback.print_exc()


def human_size(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f'{size:.2f} {unit}'
        size /= 1024.0
    return f'{size:.2f} PB'

LUA_XOR_KEY_HEX = "112136474657a78d9d8490d8ab008c35261af7e45805b8b31507d02c1e8ff6c8"
LUA_UNLUAC_URL = "https://github.com/unluac/unluac/releases/latest/download/unluac.jar"
LUA_LJD_URL = "https://github.com/nicktindall/luajit-decompiler-v2/releases/latest/download/ljd.jar"

LUA_BGMI_STD = {0: 13, 1: 14, 2: 15, 3: 16, 4: 17, 5: 18, 14: 27, 16: 29, 17: 0, 18: 1, 20: 3, 21: 4, 22: 5, 23: 6, 24: 7, 25: 8, 26: 9, 27: 10, 28: 11, 29: 12, 30: 30, 31: 31, 32: 32, 33: 33, 34: 34, 36: 36, 37: 37, 38: 38, 39: 39, 40: 40, 41: 41, 42: 42, 43: 43, 44: 44, 45: 45}
LUA_STD_BGMI = {v: k for k, v in LUA_BGMI_STD.items()}
LUA_STD_FMT = [0,1,1,0,0,0,0,0, 0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0, 0,0,0,0,0,0,2,0, 0,0,0,0,0,0,0,2, 2,0,2,0,1,0,3]

def _lua_dirs(data_path: Path):
    base = data_path / "LUA TOOL"
    return {
        "base": base,
        "org": base / "Lua_org",
        "dec": base / "Lua_Decript",
        "edit": base / "EDIT_LUA",
        "res": base / "Lua_Rueslt",
    }

def _lua_load_key(base: Path) -> bytes:
    """Embedded key; LUA TOOL/lua_xor_key.txt (hex, one line) overrides it when present."""
    key_file = base / "lua_xor_key.txt"
    if key_file.exists():
        try:
            return bytes.fromhex(key_file.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            pass
    try:
        return bytes.fromhex(LUA_XOR_KEY_HEX.strip())
    except ValueError:
        return b""

def lua_process_file(data: bytes, xor_key: bytes, is_encrypt: bool = False) -> bytes:
    """Convert BGMI Lua bytecode <-> standard Lua 5.3 bytecode.
    is_encrypt=False : game .lua  -> standard .luac (for the decompiler)
    is_encrypt=True  : standard .luac -> game .lua  (after recompiling your edits)
    """
    class RW:
        def __init__(self): self.b = bytearray()
        def byte(self, v): self.b.append(v & 0xFF)
        def u32(self, v): self.b.extend(struct.pack('<I', v))
        def i32(self, v): self.b.extend(struct.pack('<i', v))
        def raw(self, d): self.b.extend(d)
    class R:
        def __init__(self, d): self.d = d; self.p = 0
        def byte(self): v = self.d[self.p]; self.p += 1; return v
        def u32(self): v = struct.unpack_from('<I', self.d, self.p)[0]; self.p += 4; return v
        def i32(self): v = struct.unpack_from('<i', self.d, self.p)[0]; self.p += 4; return v
        def raw(self, n): v = self.d[self.p:self.p + n]; self.p += n; return v

    r, w = R(data), RW()
    hdr = bytearray(data[:33])
    if is_encrypt:
        if hdr[12:16] == b'\x04\x08\x04\x08':
            hdr[12:16] = b'\x04\x04\x04\x08'
    else:
        hdr[13] = 8  # BGMI uses size_t=4; standard Lua 5.3 is size_t=8 (unluac needs 8)
    w.raw(bytes(hdr))
    r.p = 33
    w.byte(r.byte())
    key_len = len(xor_key)

    def tg_str_read():
        sz = r.byte()
        if sz == 0xFF:
            sz = r.u32()
        if sz == 0:
            return None
        enc = r.raw(sz - 1)
        if not is_encrypt:
            if key_len == 0:
                return enc.decode('utf-8', 'replace')
            xored = bytes(enc[i] ^ xor_key[i % key_len] for i in range(len(enc)))
            try:
                decoded = xored.decode('utf-8')
                if all(c >= ' ' or c in '\t\n\r' for c in decoded):
                    return decoded
            except UnicodeDecodeError:
                pass
            return enc.decode('utf-8', 'replace')
        return enc.decode('utf-8', 'replace')

    def tg_str_write(s):
        if s is None:
            w.byte(0)
            return
        e = s.encode('utf-8') if isinstance(s, str) else s
        if is_encrypt and key_len > 0:
            e = bytes(e[i] ^ xor_key[i % key_len] for i in range(len(e)))
        sz = len(e) + 1
        if sz < 0xFF:
            w.byte(sz)
        else:
            w.byte(0xFF)
            w.u32(sz)
        w.raw(e)

    def convert(r, w):
        tg_str_write(tg_str_read())
        w.i32(r.i32())
        ldef = r.i32()
        w.i32(ldef)
        w.byte(r.byte()); w.byte(r.byte()); w.byte(r.byte())
        n = r.u32()
        w.u32(n)
        for _ in range(n):
            raw = r.u32()
            op, A, B, C, Bx, Ax = raw & 0x3F, (raw >> 6) & 0xFF, (raw >> 23) & 0x1FF, (raw >> 14) & 0x1FF, (raw >> 14) & 0x3FFFF, (raw >> 6) & 0x3FFFFFF
            sBx = Bx - 131071
            sop = LUA_STD_BGMI.get(op, op) if is_encrypt else LUA_BGMI_STD.get(op, op)
            fmt = LUA_STD_FMT[op] if is_encrypt else (LUA_STD_FMT[sop] if sop < len(LUA_STD_FMT) else 0)
            if fmt == 0:
                res = (sop & 0x3F) | (A << 6) | (C << 14) | (B << 23)
            elif fmt == 1:
                res = (sop & 0x3F) | (A << 6) | (Bx << 14)
            elif fmt == 2:
                res = (sop & 0x3F) | (A << 6) | ((sBx + 131071) << 14)
            else:
                res = (sop & 0x3F) | (Ax << 6)
            w.u32(res)
        nk = r.u32()
        w.u32(nk)
        for _ in range(nk):
            t = r.byte()
            w.byte(t)
            if t == 1:
                w.byte(r.byte())
            elif t in (3, 19):
                w.raw(r.raw(8))
            elif t in (4, 20):
                tg_str_write(tg_str_read())
        nups = r.u32()
        w.u32(nups)
        for _ in range(nups):
            w.byte(r.byte()); w.byte(r.byte())
        npt = r.u32()
        w.u32(npt)
        for _ in range(npt):
            convert(r, w)
        nln = r.u32()
        lines = []
        if is_encrypt:
            lines = [r.i32() for _ in range(nln)]
            w.u32(nln)
            prev = ldef
            for ln in lines:
                diff = ln - prev
                prev = ln
                if diff < 0:
                    diff += 256
                w.byte(diff & 0xFF)
            w.u32(0)
        else:
            cur = ldef
            for _ in range(nln):
                d = r.byte()
                cur += d if d <= 127 else d - 256
                lines.append(cur)
            w.u32(len(lines))
            for ln in lines:
                w.i32(ln)
        if not is_encrypt:
            nab = r.u32()
            for _ in range(nab):
                r.raw(8)
        nloc = r.u32()
        w.u32(nloc)
        for _ in range(nloc):
            tg_str_write(tg_str_read())
            w.i32(r.i32()); w.i32(r.i32())
        nupn = r.u32()
        w.u32(nupn)
        for _ in range(nupn):
            tg_str_write(tg_str_read())

    convert(r, w)
    return bytes(w.b)


# ---- Android edition hooks (overridden by bridge.py at runtime) ----
def safe_input(prompt: str = '') -> str:
    return ''

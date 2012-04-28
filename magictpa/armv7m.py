# This file is part of the Magic TPA project.
#
# Copyright (C) 2012  Black Sphere Technologies Ltd.
# Written by Gareth McMullin <gareth@blacksphere.co.nz>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gdb
import struct

class ARMv7M(object):
	def __init__(self, inferior):
		self._inf = inferior

		# FIXME: What is this and where is it documented?
		inferior_write_reg(self._inf, 0xE0000FB0, 0xC5ACCE55) 

		self.DWT = DWT(self._inf)
		self.TPIU = TPIU(self._inf)
		self.ITM = ITM(self._inf)
		self.DBGMCU = DBGMCU(self._inf)
		self.capture = None
	
	def trace_init(self, capture):
		"""Enable trace port in Manchester mode"""
		self.TPIU.SPPR = TPIU_SPPR_ASYNC_MANCHESTER
		self.TPIU.ACPR = 0x0010
		self.TPIU.CSPSR = TPIU_CSPSR_BYTE
		self.TPIU.FFCR = 0 # Disable formatter
		
		self.DBGMCU.CR = (
			DBGMCU_CR_TRACE_IOEN | DBGMCU_CR_TRACE_MODE_ASYNC
		)

		self.ITM.TCR = ITM_TCR_ITMENA | ITM_TCR_TXENA
		self.capture = capture

	def trace_time(self, enable=True):
		if enable:
			self.ITM.TCR |= ITM_TCR_TSENA
		else:
			self.ITM.TCR &= ~ITM_TCR_TSENA
		self.capture.hold_for_time(enable)

	def watch(self, addr, size, func):
		return TraceWatch(self, addr, size, func)


class TraceWatch(object):
	def __init__(self, dev, addr, size, func):
		"""Find and set up a watchpoint comparator"""
		found = None
		for i in range(0, dev.DWT.numcomp):
			if dev.DWT.FUNC[i] & 0xF == 0: 
				found = i
				break
		if found is None:
			raise gdb.GdbError("no watchpoint units available")

		self._addr = addr
		self._size = size
		self._wp = found

		dev.DWT.COMP[found] = addr
		dev.DWT.MASK[found] = size - 1
		dev.DWT.FUNC[found] = func

		self._dev = dev
		self._wp_pc = {}
		
	def connect(self, callback):
		cap = self._dev.capture
		if callback:
			cap.register_opcode(0x80 | (self._wp << 4), 0xF0,
					self._trigger)
			cap.register_opcode(0x47 | (self._wp << 4), 0xFF,
					self._pcsample)
			self._callback = callback
		else:
			cap.unregister_opcode(0x80 | (self._wp << 4), 0xF0)
			cap.unregister_opcode(0x47 | (self._wp << 4), 0xFF)

	def _pcsample(self, dec, op, value):
		self._wp_pc[(op >> 4) & 3] = value

	def _trigger(self, dec, op, value):
		wp = (op >> 4) & 3
		pc = self._wp_pc.get(wp, None)
		action = 'write' if op & 0x8 else 'read'
		self._callback(self, "%.6f" % dec.time, action, value, pc)

	def __str__(self):
		return ("WP comparator %d for addr 0x%X, size %d" %
			(self._wp, self._addr, self._size))

	def __del__(self):
		self._dev.DWT.FUNC[self._wp] = 0


def inferior_read_reg(inferior, addr):
	"""Read a 32-bit MMIO register from the gdb inferior"""
	mem = inferior.read_memory(addr, 4)
	return struct.unpack("<L", mem)[0]

def inferior_write_reg(inferior, addr, val):
	"""Write a 32-bit MMIO register to the gdb inferior"""
	mem = struct.pack("<L", val)
	inferior.write_memory(addr, mem)

class RegArray(object):
	def __init__(self, inf, t):
		self._inf = inf
		self._t = t

	def __getitem__(self, i):
		t = self._t[0] + self._t[1] * i
		v = inferior_read_reg(self._inf, t)
		return v

	def __setitem__(self, i, val):
		t = self._t[0] + self._t[1] * i
		inferior_write_reg(self._inf, t, val)

class MMIO(object):
	def __init__(self, inf):
		self._inf = inf

	def __setattr__(self, name, val):
		if name in self.__class__.regs.keys():
			inferior_write_reg(self._inf, self.__class__.regs[name], val)
		else:
			self.__dict__[name] = val

	def __getattr__(self, name):
		if name in self.__class__.regs.keys():
			t = self.__class__.regs[name]
			if type(t) is tuple:
				return RegArray(self._inf, t)
			else:
				return inferior_read_reg(self._inf, t)
		else:
			return self.__dict__[name]
	
class TPIU(MMIO):
	"""Trace Port Interface Unit"""
	regs = {
		'SSPSR': 0xE0040000,
		'CSPSR': 0xE0040004,
		'ACPR': 0xE0040010,
		'SPPR': 0xE00400F0,
		'FFSR': 0xE0040300,
		'FFCR': 0xE0040304,
		'TYPE': 0xE0040FC8,
	}
# TPIU bit definitions
TPIU_CSPSR_BYTE = 0x1
TPIU_SPPR_ASYNC_MANCHESTER = 0x1

class DWT(MMIO):
	"""Data Watchpoint and Trace"""
	regs = {
		'CTRL': 0xE0001000,
		'CYCCNT': 0xE0001004,
		'CPICNT': 0xE0001008,
		'EXCCNT': 0xE000100C,
		'SLEEPCNT': 0xE0001010,
		'LSUCNT': 0xE0001014,
		'FOLDCNT': 0xE0001018,
		'PCSR': 0xE000101C,
		'COMP': (0xE0001020, 16),
		'MASK': (0xE0001024, 16),
		'FUNC': (0xE0001028, 16),
	}
	def __init__(self, inf):
		MMIO.__init__(self, inf)
		self.numcomp = self.CTRL >> 28;

# DWT bit definitions
DWT_MASK_BYTE = 0x0
DWT_MASK_HALFWORD = 0x1
DWT_MASK_WORD = 0x3
DWT_FUNC_FUNC_WRITE = 0x6

class ITM(MMIO):
	"""Instrumentation and Trace Macrocell"""
	regs = {
		'TCR': 0xE0000E80,
	}
# ITM bit definitions
ITM_TCR_ITMENA = 0x1
ITM_TCR_TSENA = 0x2
ITM_TCR_TXENA = 0x8

class DBGMCU(MMIO):
	regs = {
		'CR': 0xE0042004,
	}
# DBGMCU bit definitions
DBGMCU_CR_TRACE_IOEN = 0x00000020
DBGMCU_CR_TRACE_MODE_ASYNC = 0x00000000


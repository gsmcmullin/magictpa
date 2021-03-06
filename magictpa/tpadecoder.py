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

import time

class TPADecoder(object):
	"""Decoder state machine for unformatted trace port"""
	siztab = (0, 1, 2, 4)
	IDLE = 0
	WAIT_SIZE = 1
	WAIT_CONT = 2

	def __init__(self):
		self._state = TPADecoder.IDLE
		self._opcodes = [
			(0x00, 0xFF, TPADecoder._sync, ())
		]
		self._pause = True
		self._timehold = False
		self._queue = []

	def register_opcode(self, code, mask, func, *args):
		self._opcodes.append((code, mask, func, args))

	def unregister_opcode(self, code, mask):
		for i in range(len(self._opcodes)):
			if ((self._opcodes[i][0] == code) and
			    (self._opcodes[i][1] == mask)):
				del self._opcodes[i]
				return

	def hold_for_time(self, hold=True):
		self._timehold = hold
		self.time = 0 if hold else time.time()

	def decode(self, s):
		for c in s:
			self.decode_byte(c)

	def decode_byte(self, c):
		if self._state == TPADecoder.IDLE:
			if not self._timehold:
				self.time = time.time()
			self._opcode = c
			self._param = 0
			if c & 0x3:
				self._state = TPADecoder.WAIT_SIZE
				self._size = self.siztab[c & 3]
				self._count = 0
			elif c & 0x80:
				self._state = TPADecoder.WAIT_CONT
				self._count = 0
			else:
				self._push_opcode(c, None)
		elif self._state == TPADecoder.WAIT_SIZE:
			self._param += c << (8*self._count)
			self._count += 1
			if self._count == self._size:
				self._push_opcode(self._opcode, self._param)
		elif self._state == TPADecoder.WAIT_CONT:
			self._param |= (c & 0x7F) << self._count
			self._count += 7
			if c & 0x80 == 0:
				self._push_opcode(self._opcode, self._param)
		else:
			raise Exception("Invalid decoder state!")

	def _timestamp(self, opcode, val):
		if opcode & 0xC0 == 0xC0:
			# long format
			return val
		if ((opcode & 0x8F) == 0) and ((opcode & 0x70) != 0x70):
			# short format
			return opcode >> 4

	def _push_opcode(self, opcode, param):
		self._state = TPADecoder.IDLE
		if self._pause:
			return

		if not self._timehold:
			self._exec_opcode(opcode, param)
		else:
			ts = self._timestamp(opcode, param)
			if not ts:
				# This isn't a timestamp
				self._queue.append((opcode, param))
			else:
				# This is a timestamp, flush queue
				self.time += ts
				for o, p in self._queue:
					self._exec_opcode(o, p)
				self._queue = []

	def _exec_opcode(self, opcode, param):
		#print "opcode %02X %s" % (opcode, param)
		for t in self._opcodes:
			if opcode & t[1] == t[0]:
				t[2](self, opcode, param, *t[3])
				return

	def _sync(self, opcode, param):
		pass


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
import usb.core
import usb.util
import threading
import sys

from tpadecoder import TPADecoder

def printopcode(dec, opcode, param, s):
	print s

def check_serial(dev, serial):
	if not dev.iSerialNumber:
		return False

	if sys.platform == 'darwin':
		return True

	s = usb.util.get_string(dev, 8, dev.iSerialNumber)
	return s == serial

class TPACapture(threading.Thread, TPADecoder):
	def __init__(self, serial, ifno, epno):
		threading.Thread.__init__(self)
		self.daemon = True
		TPADecoder.__init__(self)
		self.dev = usb.core.find(idVendor=0x1d50, idProduct=0x6018,
			custom_match=lambda d: check_serial(d, serial)
		)
		config = self.dev[0]
		iface = tuple(config)[ifno]
		self.endp = tuple(iface)[0]

		self.lock = threading.RLock()
		self.rawfile = None

		self.register_opcode(0x70, 0xFF, printopcode, "OVERFLOW!")

	def set_rawfile(self, filename):
		self.lock.acquire()
		self.rawfile = open(filename, "w") if filename else None
		self.lock.release()

	def pause(self):
		self.lock.acquire()
		self._pause = True
		self.lock.release()

	def resume(self):
		self.lock.acquire()
		self._pause = False
		self.lock.release()

	def register_opcode(self, code, mask, func, *args):
		self.lock.acquire()
		def op_proxy(dec, op, param, *args):
			gdb.post_event(lambda: func(dec, op, param, *args))
		TPADecoder.register_opcode(self, code, mask, op_proxy, *args)
		self.lock.release()

	def unregister_opcode(self, code, mask):
		self.lock.acquire()
		TPADecoder.unregister_opcode(self, code, mask)
		self.lock.release()

	def run(self):
		while True:
			try:
				data = self.endp.read(256)
			except usb.core.USBError:
				continue

			self.lock.acquire()
			if self.rawfile:
				self.rawfile.write(data.tostring())
				self.rawfile.flush()
			self.decode(data)
			self.lock.release()


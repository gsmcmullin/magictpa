# This file is part of the Magic TPA project.
#
# Copyright (C) 2013  Black Sphere Technologies Ltd.
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
from magictpa.tpacapture import capture

class ParameterTpaRawFile(gdb.Parameter):
	"""TPA raw logfile"""
	def __init__(self):
		self.set_doc = "Record raw (binary) trace stream to a file."
		self.show_doc = "File raw (binary) trace stream is captured to."
		gdb.Parameter.__init__(self, "tpa rawfile", gdb.COMMAND_SUPPORT,
			gdb.PARAM_OPTIONAL_FILENAME)
	def get_set_string(self):
		capture.set_rawfile(self.value)
		if self.value:
			return "Logging trace stream to %s." % self.value
		else:
			return "Not logging trace stream."
	def get_show_string(self, svalue):
		if self.value:
			return "Logging trace stream to %s." % self.value
		else:
			return "Not logging trace stream."
tpa_rawfile = ParameterTpaRawFile()

class ParameterTpaGate(gdb.Parameter):
	def __init__(self):
		self.set_doc = "Gate TPA while target halted"
		self.show_doc = "Gate TPA while target halted"
		gdb.Parameter.__init__(self, "tpa gate", gdb.COMMAND_SUPPORT,
			gdb.PARAM_BOOLEAN)
		gdb.events.cont.connect(self.cont_handler)
		gdb.events.stop.connect(self.stop_handler)
		self.running = False
		self.value = True

	def get_set_string(self):
		if not self.running:
			if self.value:
				capture.pause()
			else:
				capture.resume()
		return "TPA capture is " + ("gated" if self.value else "not gated")

	def get_show_string(self, svalue):
		return "TPA capture is " + ("gated" if self.value else "not gated")

	def cont_handler(self, event):
		self.running = True
		capture.resume()
	def stop_handler(self, event):
		self.running = False
		if self.value:
			capture.pause()
tpa_gate = ParameterTpaGate()

class ParameterTpaEcho(gdb.Parameter):
	"""Echo decoded trace to stdout"""
	def __init__(self):
		self.set_doc = "Echo decoded trace to stdout"
		self.show_doc = "Echo decoded trace to stdout"
		gdb.Parameter.__init__(self, "tpa echo", gdb.COMMAND_SUPPORT,
			gdb.PARAM_BOOLEAN)
	def get_set_string(self):
		if self.value:
			return "Trace written to stdout"
		else:
			return "Trace not written to stdout"
	def get_show_string(self, svalue):
		if self.value:
			return "Trace written to stdout"
		else:
			return "Trace not written to stdout"
tpa_echo = ParameterTpaEcho()

class ParameterTpaLog(gdb.Parameter):
	"""TPA logfile"""
	def __init__(self):
		self.set_doc = "Record decoded trace stream to a file."
		self.show_doc = "File decoded trace stream is captured to."
		gdb.Parameter.__init__(self, "tpa log", gdb.COMMAND_SUPPORT,
			gdb.PARAM_OPTIONAL_FILENAME)
		self.logfile = None
	def get_set_string(self):
		if self.logfile:
			self.logfile.flush()
		if self.value:
			self.logfile = open(self.value, "a")
			self.write("TPA logfile opened\n");

		if self.value:
			return "Logging trace stream to %s." % self.value
		else:
			return "Not logging trace stream."
	def get_show_string(self, svalue):
		if self.value:
			return "Logging trace stream to %s." % self.value
		else:
			return "Not logging trace stream."
	def write(self, event):
		if self.value:
			self.logfile.write(event)
			self.logfile.flush()
		if tpa_echo.value or not self.value:
			gdb.write(event)
tpa_log = ParameterTpaLog()


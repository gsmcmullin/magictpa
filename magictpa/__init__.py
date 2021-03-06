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

print "Black Magic Trace Extention for GDB (MagicTPA) - 0.1"
print "Copyright (C) 2012  Black Sphere Technologies Ltd."
print "License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>"

# Some sanity checks
if gdb.VERSION < '7.4':
	raise gdb.GdbError("GDB verison < 7.4.  GDB 7.4 or greater is requred!");

if gdb.parameter("mem inaccessible-by-default"):
	raise gdb.GdbError("Please add 'set mem inaccessible-by-default off' to your .gdbinit")
if not gdb.parameter("target-async"):
	raise gdb.GdbError("Please add 'set target-async on' to your .gdbinit")

import magictpa.armv7m
from magictpa.tpacapture import capture
from magictpa.tpacommands import tpa_log

# We really need to do this when notified of a new inforior.
cm3 = magictpa.armv7m.ARMv7M(gdb.selected_inferior())
cm3.trace_init(capture)

def inferior_created_cb(event):
	print "New inferior!"
	cm3 = magictpa.armv7m.ARMv7M(event.inferior)
	cm3.trace_init(capture)

try:
	gdb.events.created.connect(inferior_created_cb)
except:
	# This functionality doesn't yet exist in GDB.
	pass

class ParameterTpaSpeed(gdb.Parameter):
	def __init__(self):
		self.set_doc = "Set async trace port prescaler"
		self.show_doc = "Show async trace port prescaler"
		gdb.Parameter.__init__(self, "tpa speed", gdb.COMMAND_SUPPORT, 
			gdb.PARAM_ZINTEGER)
		self.value = 0x0010
	def get_set_string(self):
		cm3.TPIU.ACPR = self.value
		return "TPA Speed is now 0x%04X" % self.value
	def get_show_string(self, svalue):
		return "TPA Speed is 0x%04X" % self.value
tpa_speed = ParameterTpaSpeed()

class ParameterTpaTime(gdb.Parameter):
	"""Valid options are 'off', 'host', or 'delta'.
	If off, no timestamp information will be logged.
	If host, trace information will be timestamped with Python time.time().
	If delta, local differential timestamps generated by the TPIU will be used.
	"""
	def __init__(self):
		self.set_doc = "Set TPA timestamp mode"
		self.show_doc = "Show TPA timestamp mode"
		gdb.Parameter.__init__(self, "tpa time", gdb.COMMAND_SUPPORT, 
			gdb.PARAM_ENUM, ("off", "host", "delta"))

	def get_set_string(self):
		if self.value == 'delta':
			cm3.trace_time(True)
		else:
			cm3.trace_time(False)

		return ""
tpa_time = ParameterTpaTime()

class ParameterTpaTraceExceptions(gdb.Parameter):
	def __init__(self):
		gdb.Parameter.__init__(self, "tpa trace-exceptions", 
			gdb.COMMAND_SUPPORT, gdb.PARAM_BOOLEAN)
	def _trigger(self, time, action, value):
		tpa_log.write("%s %d\n" % (action, value))

	def get_set_string(self):
		if self.value:
			cm3.trace_exc(self._trigger)
			return "Exception tracing is now on"
		else:
			cm3.trace_exc(None)
			return "Exception tracing is now off"
tpa_traceexc= ParameterTpaTraceExceptions()

class CommandTpaWatch(gdb.Command):
	"""Trace a program variable"""
	def __init__(self):
		gdb.Command.__init__(self, "tpa watch", gdb.COMMAND_SUPPORT)
		self.nextwatch = 1
		self.watches = {}

	def trigger(self, wp, time, action, value, pc):
		value = gdb.Value(value).cast(wp.vartype)
		if pc:
			sal = gdb.decode_line("*" + hex(pc))[1][0]
			pc = "%s:%d" % (sal.symtab.filename, sal.line)
		else:
			pc = ''
		if tpa_time.value == 'off':
			time = ''
		action = "%5s %s=%d" % (action, wp.varname, value)
		tpa_log.write("%s %-25s %s\n" % (time, action, pc))

	def invoke(self, args, from_tty):
		argv = gdb.string_to_argv(args)
		self.varname = argv[0]
		val = gdb.parse_and_eval(argv[0])
		addr = int(str(val.address).split(' ')[0], 16)
		size = val.type.sizeof
		samplepc = False
		if len(argv) == 2:
			for i in argv[1].split(','):
				if i == 'pc':
					samplepc = True
				else:
					raise gdb.GdbError("unknown mode: " + i)

		wp = cm3.watch(addr, size, 0x03 if samplepc else 0x02)
		wp.connect(self.trigger)
		wp.varname = argv[0]
		wp.vartype = val.type
		self.watches[self.nextwatch] = wp
		print "%d:%s" % (self.nextwatch, wp)
		self.nextwatch += 1

tpa_watch = CommandTpaWatch()

class CommandTpaDelete(gdb.Command):
	"""Remove a trace source"""
	def __init__(self):
		gdb.Command.__init__(self, "tpa delete", gdb.COMMAND_SUPPORT)

	def invoke(self, args, from_tty):
		i = int(args)
		tpa_watch.watches[i].connect(None)
		del tpa_watch.watches[i]

tpa_delete = CommandTpaDelete()

class CommandTpaStim(gdb.Command):
	"""Trace ITM Stimulus"""
	def __init__(self):
		gdb.Command.__init__(self, "tpa stim", gdb.COMMAND_SUPPORT)

	def _trigger(self, channel, value):
		tpa_log.write("STIM %d: %s" % (channel, value))

	def invoke(self, args, from_tty):
		argv = gdb.string_to_argv(args)
		cm3.trace_stim(int(argv[0]), self._trigger)

tpa_stim = CommandTpaStim()


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

class CommandTpa(gdb.Command):
	"""Commands for controling trace port analysis."""
	def __init__(self):
		gdb.Command.__init__(self, "tpa", gdb.COMMAND_SUPPORT,
			prefix=True)
CommandTpa()

# These command 'set tpa' and 'show tpa' are needed for the parameters
# below to be accepted by GDB.
class CommandSetTpa(gdb.Command):
	"""Set parameters for trace port analysis."""
	def __init__(self):
		gdb.Command.__init__(self, "set tpa", gdb.COMMAND_SUPPORT,
			prefix=True)
CommandSetTpa()
class CommandShowTpa(gdb.Command):
	"""Show parameters for trace port analysis."""
	def __init__(self):
		gdb.Command.__init__(self, "show tpa", gdb.COMMAND_SUPPORT,
			prefix=True)
CommandShowTpa()

from magictpa.tpacommands.hostparams import *


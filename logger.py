from os import _exit
def log(s, die=False):
	print s
	sys.stdout.flush()
	if die: _exit(1)
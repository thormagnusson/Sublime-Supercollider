import sublime, sublime_plugin
import sys
import subprocess
import threading
import os
import webbrowser

try:
	from Queue import Queue, Empty
except ImportError:
	from queue import Queue, Empty  # python 3.x

def enqueue_output(out, queue):
	for line in iter(out.readline, b''):
		queue.put(line)
	out.close()

# command to start SuperCollider interpreter sclang
class Sc_startCommand(sublime_plugin.WindowCommand):
	sclang_process = None
	sclang_queue = None
	sclang_thread = None
	output_view = None
	panel_name = None

	def run(self):
		# create post window
		if Sc_startCommand.output_view is None:
			Sc_startCommand.panel_name = "post window"

	# 	THIS IS THE SUBLIME CONSOLE
	#		Sc_startCommand.output_view = self.window.get_output_panel(Sc_startCommand.panel_name)
	# 	BUT THE FOLLOWING THREE LINES ARE THE SUPERCOLLIDER POST WINDOW   
	        Sc_startCommand.output_view = self.window.new_file()
	        Sc_startCommand.output_view.set_scratch(True)
	        Sc_startCommand.output_view.set_name(Sc_startCommand.panel_name)
	        
		# start supercollider
		if Sc_startCommand.sclang_thread is None or not Sc_startCommand.sclang_thread.isAlive():
			settings = sublime.load_settings("SuperCollider.sublime-settings")
			sc_dir = settings.get("sc_dir")
			sc_exe = settings.get("sc_exe")

			if os.name == 'posix':
				Sc_startCommand.sclang_process = subprocess.Popen(
					[sc_dir + sc_exe, '-i', 'sublime'],
					bufsize = 0,
					stdin = subprocess.PIPE,
					stdout = subprocess.PIPE,
					stderr = subprocess.STDOUT,
					close_fds = True)
			else:
				Sc_startCommand.sclang_process = subprocess.Popen(
					[sc_exe, '-i', 'sublime'], 
					cwd = sc_dir, 
					bufsize = 0, 
					stdin = subprocess.PIPE, 
					stdout = subprocess.PIPE, 
					stderr = subprocess.STDOUT,
					shell = True)
			
			Sc_startCommand.sclang_queue = Queue()
			Sc_startCommand.sclang_thread = threading.Thread(target=enqueue_output, args=(Sc_startCommand.sclang_process.stdout, Sc_startCommand.sclang_queue))
			Sc_startCommand.sclang_thread.daemon = True # thread dies with the program
			Sc_startCommand.sclang_thread.start()
			sublime.status_message('Starting SuperCollider')

		sublime.set_timeout(self.scrolldown, 100)
		sublime.set_timeout(self.poll, 1000)

	def poll(self):
		# continue while sclang is running
		if Sc_startCommand.sclang_thread is not None and Sc_startCommand.sclang_thread.isAlive():
			scReturnedSomething = True;
			somethingHappened = False

			edit = Sc_startCommand.output_view.begin_edit()

			while scReturnedSomething:
				try:  line = Sc_startCommand.sclang_queue.get_nowait()
				except Empty:
					scReturnedSomething = False
				else:
					somethingHappened = True 
					try: Sc_startCommand.output_view.insert(edit, Sc_startCommand.output_view.size(), line.encode(sys.getfilesystemencoding()))
					except UnicodeDecodeError:
						print "Encoding error..."

			Sc_startCommand.output_view.end_edit(edit)

			if somethingHappened :
				sublime.set_timeout(self.scrolldown, 50)
				
			sublime.set_timeout(self.poll, 250)

	def scrolldown(self):
		if Sc_startCommand.output_view is not None:
			Sc_startCommand.output_view.show(Sc_startCommand.output_view.size()) # scroll down
			self.window.run_command("show_panel", {"panel": "output." + Sc_startCommand.panel_name})

# command to stop SuperCollider interpreter sclang
class Sc_stopCommand(sublime_plugin.WindowCommand):
	def run(self):
		if Sc_startCommand.sclang_thread is not None and Sc_startCommand.sclang_thread.isAlive():
			#Sc_startCommand.sclang_process.stdin.write("0.exit;\x0c")
			Sc_startCommand.sclang_process.stdin.write(bytes("0.exit;\x0c"))
			Sc_startCommand.sclang_process.stdin.flush()
			sublime.status_message('stop sclang.')

# command to send the current line to sclang
class Sc_sendCommand(sublime_plugin.WindowCommand):
	def run(self):
		if Sc_startCommand.sclang_thread is not None and Sc_startCommand.sclang_thread.isAlive():
			view = self.window.active_view()
			sel = view.sel()
			point = sel[0]
			line = view.line(point)
			line_str = view.substr(line)
			if line_str[0] == '(' or line_str[0] == ')':
				view.run_command("expand_selection", {"to": "brackets"})
			sel = view.sel()
			region = view.line(sel[0])
			lines = view.substr(region)
			Sc_startCommand.sclang_process.stdin.write(bytes(lines))
			Sc_startCommand.sclang_process.stdin.write(bytes("\x0c"))
			Sc_startCommand.sclang_process.stdin.flush()

# command to show the supercollider console
class Sc_show_consoleCommand(sublime_plugin.WindowCommand):
	def run(self):
		if Sc_startCommand.output_view is not None:
			Sc_startCommand.output_view.show(Sc_startCommand.output_view.size()) # scroll down
			self.window.run_command("show_panel", {"panel": "output." + Sc_startCommand.panel_name})

# hide console
class Sc_hide_consoleCommand(sublime_plugin.WindowCommand):
	def run(self):
		if Sc_startCommand.output_view is not None:
			Sc_startCommand.output_view.show(Sc_startCommand.output_view.size()) # scroll down
			self.window.run_command("hide_panel", {"panel": "output." + Sc_startCommand.panel_name})

# clear console log
class Sc_clear_consoleCommand(sublime_plugin.WindowCommand):
	def run(self):
		if Sc_startCommand.output_view is not None:
			edit = Sc_startCommand.output_view.begin_edit()
			region = sublime.Region(0, Sc_startCommand.output_view.size());
			Sc_startCommand.output_view.erase(edit, region);
			Sc_startCommand.output_view.end_edit(edit)
			sublime.status_message('Clear console logs.')

# stop all sounds
class Sc_stop_all_soundsCommand(sublime_plugin.WindowCommand):
	def run(self):
		if Sc_startCommand.sclang_thread is not None and Sc_startCommand.sclang_thread.isAlive():
			Sc_startCommand.sclang_process.stdin.write(bytes("thisProcess.stop;\x0c"))
			Sc_startCommand.sclang_process.stdin.flush()
			sublime.status_message('thisProcess.stop.')

# recompile class library
class Sc_recompileCommand(sublime_plugin.WindowCommand):
	def run(self):
		if Sc_startCommand.sclang_thread is not None and Sc_startCommand.sclang_thread.isAlive():
			Sc_startCommand.sclang_process.stdin.write(bytes("\x18"))
			Sc_startCommand.sclang_process.stdin.flush()

# Boot default server
class Sc_boot_serverCommand(sublime_plugin.WindowCommand):
	def run(self):
		if Sc_startCommand.sclang_thread is not None and Sc_startCommand.sclang_thread.isAlive():
			Sc_startCommand.sclang_process.stdin.write(bytes("Server.default.boot;\x0c"))
			Sc_startCommand.sclang_process.stdin.flush()


# show GUI for default server
class Sc_server_guiCommand(sublime_plugin.WindowCommand):
	def run(self):
		if Sc_startCommand.sclang_thread is not None and Sc_startCommand.sclang_thread.isAlive():
			Sc_startCommand.sclang_process.stdin.write(bytes("Server.default.makeGui;\x0c"))
			Sc_startCommand.sclang_process.stdin.flush()

# open help browser for selected word
class Sc_search_helpCommand(sublime_plugin.WindowCommand):
	def run(self):
		if Sc_startCommand.sclang_thread is not None and Sc_startCommand.sclang_thread.isAlive():
			view = self.window.active_view()
			sel = view.sel()
			point = sel[0]
			word = view.word(point)
			Sc_startCommand.sclang_process.stdin.write(bytes("HelpBrowser.openHelpFor(\"" + view.substr(word) + "\");\x0c"))
			Sc_startCommand.sclang_process.stdin.flush()

# Open a class file in Sublime (ask SC to find the file - because of user extensions)
class Sc_open_classCommand(sublime_plugin.WindowCommand):
	def run(self):
		if Sc_startCommand.sclang_thread is not None and Sc_startCommand.sclang_thread.isAlive():
			view = self.window.active_view()
			sel = view.sel()
			point = sel[0]
			word = view.word(point)
			#sublime.active_window().open_file("/Users/thor/Desktop/test.xtm") # need to get SC to return path to ST
			Sc_startCommand.sclang_process.stdin.write(bytes( "(\"open -a 'Sublime Text 2.app'\" + " + view.substr(word) + ".filenameSymbol.asString.escapeChar($ )).unixCmd;\x0c" ))
			Sc_startCommand.sclang_process.stdin.flush()

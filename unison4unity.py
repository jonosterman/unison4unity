#!/usr/bin/env python
"""
 Copyright (C) 2013 / me

 Licensed under the Apache License, Version 2.0 (the "License").
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

import appindicator
import glob
import gtk
import os
import re
import subprocess
import sys
import time
import datetime
import logging
import pynotify
from multiprocessing import Process, Queue

#logging.basicConfig(filename='/tmp/unison4unity.log',level=logging.DEBUG)
logging.basicConfig(format='[%(levelname)s] %(message)s',level=logging.DEBUG)
POOL_DELAY = 120 # 120 seconds
runCnt = 0 # how many time it already looped
queue = Queue()

class UnisonWrap:

	def menuStd(self, list):
		## notification
		## if some file(s) changed : build a list and display popup
		hasError = False
		if len(list) > 0:
			self.lastChanges = []
			for m in list:
				if 'error' in m:
					## error entry
					hasError = True
					## notify
					n = pynotify.Notification("Unison Error", "Error in profile [{0}]".format(m['error']))
					n.set_timeout(2)
					n.show()
				else:
					self.lastChanges.append(m)

		## rebuild menu
		self.menu = gtk.Menu()
		## * timestamp
		status="Last update : {0} files, {1}".format(len(self.lastChanges), self.timestamp.strftime("%H:%M %d %b"))
		ts_item = gtk.MenuItem(status)
		ts_item.connect("activate", self.details)
		
		ts_item.show()
		self.menu.append(ts_item)
		## * Quit
		image = gtk.ImageMenuItem(gtk.STOCK_QUIT)
		image.connect("activate", self.quit)
		image.show()
		self.menu.append(image)
		## show menu
		self.menu.show()
		self.ind.set_menu(self.menu)
		##
		if hasError:
			self.ind.set_attention_icon("dialog-warning")
		else:
			self.ind.set_attention_icon("account-logged-in")
		
	def menuDemo(self):
		## create a menu
		self.menu = gtk.Menu()
		## wait message
		ts_item = gtk.MenuItem("Initial sync...")
		ts_item.show()
		self.menu.append(ts_item)
	
		image = gtk.ImageMenuItem(gtk.STOCK_QUIT)
		image.connect("activate", self.quit)
		image.show()
		self.menu.append(image)
				    
		self.menu.show()
		self.ind.set_menu(self.menu)

		
	##
	## Consructor
	##
	def __init__(self):
		self.timestamp = datetime.datetime.now()
		self.lastChanges = []
		self.unisonProfiles = []
		logging.debug("Setup Indicator")
		self.ind = appindicator.Indicator("unison","unison-messages",appindicator.CATEGORY_APPLICATION_STATUS)
		self.ind.set_status(appindicator.STATUS_ATTENTION)
		self.ind.set_attention_icon("account-logged-in")
		pynotify.init("unison")
		self.menuDemo()

	##
	## Menu callback "Quit"
	##
	def quit(self, widget):
		gtk.main_quit()	
		exit(0)

	##
	## Menu callback "Details"
	##
	def details(self, widget):
		strArr = []
		for m in self.lastChanges:
			strArr.append("{0} {1}".format(m['dir'], m['file']))			
	
		## notify
		n = pynotify.Notification("Unison Last Changes", "\n".join(strArr) )
		n.set_timeout(2)
		n.show()

	##
	## start perodical scan
	##
	def start(self):
		# first run (after 1 sec.)
		gtk.timeout_add(1000, self.runAsync)
		gtk.main()

	def runAsync(self):
		global runCnt
		global queue
		runCnt += 1
		if queue.qsize() == 1 : 
			#logging.debug("run #%d. skip since already syncing",	runCnt)
			return True
		elif queue.qsize() > 1 : 
			logging.debug("run #%d. should probably unlock it and process list in queue [size: %d] ?...",	runCnt, queue.qsize())
			## remove both object in queue (must be 2 : 'lock' and 'file list')			
			list = []
			while queue.qsize() > 0:
				a = queue.get()
				if a != "lock":
					list = a
			## rebuild UI
			self.menuStd(list)
			## continue			
			return True
		else :
			## add a dummy lock object to be able to test if sub process is still
			## running
			queue.put("lock")

			## start sync in other process (not blocking GTK thread)
			p = Process(target=self.syncAllProfiles, args=(runCnt,queue))
			p.daemon=True
			p.start()
			## return True or False depeneding if it is the first run or not.
			if runCnt == 1:
				## do not renew gtk timeout since we want to increase it: set
				## new timeout trigger and cancel current by returning false
				#logging.debug("run #%d. sync started. return False since first run.",	runCnt)		
				gtk.timeout_add(POOL_DELAY * 1000, self.runAsync)
				return False
			else:
				#logging.debug("run #%d. sync started. return True since not first run.",	runCnt)		
				return True

	def syncAllProfiles(self, cnt, queue):
		## timestamp
		self.timestamp = datetime.datetime.now()
		#logging.debug("unison check run #%s at [%s]",	runCnt, self.timestamp.strftime("%Y.%m.%d - %H:%M:%S"))
		## get profiles
		profiles = self.getProfiles();
		#logging.debug("found [%s] profiles",len(profiles))
		## for each profile, perform sync
		list = []
		for profile in profiles:
			try:
				sub = self.syncProfile(profile)
				if sub != None:
					list += sub
			except:
				logging.error("Failed to sync profile [%s]",profile)
				list.append({ 'error': profile })
		## release lock
		#logging.debug("Add files list in queue for main thread.")
		queue.put(list)
		

	##
	## return a list of unison profile to sync based on files in ${HOME}/.unison
	##
	def getProfiles(self):
		profiles = []
		try:
			## base directory
			os.chdir(os.path.expanduser('~/.unison'))
			## list '.prf' files but exclude default.prf
			for files in glob.glob("*.prf"):
				if files != "default.prf":
					profiles.append(re.sub(".prf$","",files))
			return profiles
		except:
			logging.error("Failed to list unison profiles")
			return []


	##
	## Perform unsion sync on profile
	##
	def syncProfile(self, profile):
		files = []
		logging.debug("Proceed profile [%s]",profile)
		output = subprocess.check_output(["unison","-ui","text","-batch",profile], stderr=subprocess.STDOUT)
		## regexp to extract content from unison output
		pOut = re.compile(".{9}---->\s+(.*)")
		pIn = re.compile("\s+<----.{9}\s+(.*)")
		pEnd = re.compile("Synchronization complete at[0-9: ]+\(([0-9]+) item transferred, ([0-9]+) skipped, ([0-9]+) failed\)")
		## go through all lines
		for line in output.split('\n'):
			## match first 
			m = pOut.match(line)
			if m:
				logging.debug("upload local changes for file [%s]",m.group(1).strip())
				files.append({ 'file': m.group(1), 'dir':">",'profile':profile })
			else:
				m = pIn.match(line)
				if m:
					logging.debug("download remote changes for file [%s]",m.group(1).strip())
					files.append({ 'file': m.group(1), 'dir': "<",'profile':profile })
				else:
					## check if last ligne has been reached
					m = pEnd.match(line)
					if m:
						tr = m.group(1)
						sk = m.group(2)
						fa = m.group(3)
						logging.debug("unison completed [%s transferred, %s skipped, %s failed]",tr,sk,fa)
						return files
					#else:
					#	print("[unknown-line] {0}".format(line))
		return None


## main
if __name__ == "__main__":
	## create indicator UI
	indicator = UnisonWrap()
	## start app
	indicator.start()


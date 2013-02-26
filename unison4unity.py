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
import logging

logging.basicConfig(filename='/tmp/unison4unity.log',level=logging.DEBUG)
POOL_DELAY = 120 # seconds

class UnisonProfile:
    def __init__(self, name, localDir):
      self.name = name
      self.localDir = localDir

class UnisonWrap:
    def __init__(self):
      self.timestamp = time.ctime()
      self.unisonProfiles = []
      self.ind = appindicator.Indicator("unison-indicator",
                                        "unison-messages",
                                        appindicator.CATEGORY_APPLICATION_STATUS)
      self.ind.set_status(appindicator.STATUS_ATTENTION)
      self.ind.set_attention_icon("account-logged-in")
      self.menu_setup()

    def menu_setup(self):
        logging.debug("Rebuild menu..")
        self.menu = gtk.Menu()
        ## timestamp
        ts_item = gtk.MenuItem("Last Update: "+self.timestamp)
        ts_item.show()
        self.menu.append(ts_item)

        ## profiles
        for p in self.unisonProfiles :
          logging.debug("add ["+p+"]")  
          item = gtk.MenuItem(p)
          item.connect("activate", self.openProfile, p)
          item.show()
          self.menu.append(item)
        ## Unison
        self.unison_item = gtk.MenuItem("Unison...")
        self.unison_item.connect("activate", self.openUnison)
        self.unison_item.show()
        self.menu.append(self.unison_item)
        ## Quit
        self.quit_item = gtk.MenuItem("Quit")
        self.quit_item.connect("activate", self.quit)
        self.quit_item.show()
        self.menu.append(self.quit_item)
        ##
        self.ind.set_menu(self.menu)

    def main(self):
        # initial run
        self.check_unison()
        # next runs
        gtk.timeout_add(POOL_DELAY * 1000, self.check_unison)
        gtk.main()

    def openProfile(self, widget, profile):
        subprocess.call(["unison","-ui","graphic",profile])

    def openUnison(self, widget):
        subprocess.call(["unison","-ui","graphic"])

    def quit(self, widget):
        sys.exit(0)

    def check_unison(self):
      self.timestamp = time.ctime()
      ## list unison profiles
      self.unisonProfiles = self.listUnisonProfiles()
      ## update menu
      self.menu_setup()
      ## run text-mode unison in batch mode for each profile
      # @todo: only sync profiles listed in config
      error = 0
      for p in self.unisonProfiles :
        logging.debug("Start unison for profile [" + p +"]")
        if subprocess.call(["unison","-ui","text","-batch",p]) != 0:
          logging.error("unison call failed")
          error += 1
        else:
          logging.debug("unison call succeed")
        ## update icon
        if error > 0:
          self.ind.set_attention_icon("dialog-warning")
        else:
          self.ind.set_attention_icon("account-logged-in")
      ## next iteration
      return True

    ## List profile files in unison directory
    def listUnisonProfiles(self):
      profiles = []
      try:
        os.chdir(os.path.expanduser('~/.unison'))
        for files in glob.glob("*.prf"):
          if files != "default.prf":
            profiles.append(re.sub(".prf$","",files))
        return profiles
      except:
        logging.error("Failed to list unison profiles")
        return []


if __name__ == "__main__":
    indicator = UnisonWrap()
    indicator.main()


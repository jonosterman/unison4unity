unison4unity
============

Wrapper python script for unison to play well with unity notification area.

Unison is a great synchronization tool that allow to sync local 
folders with remote locations. 

Its default install lacks desktop integration. This wrapper script
run unison periodically. Display last sync status (success or fail) 
and let user access unison from unity notification area.

At this time (feb 2013) this script is very basic but works.

Feel free to fork and contribute!!

== What is does ==

 * list profiles found in ~/.unison
 * run unison in batch mode for each profile
 * update status icon
 * wait 2 minutes and loop

Log files are in /tmp/.

== Installation ==
 * copy the python script somewhere in your home. 
 * Add it in  Ubuntu 'Startup Application' list.
 * login / logout




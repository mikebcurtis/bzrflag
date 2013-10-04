#!/usr/bin/python -tt

from bzrc import BZRC, Command
import sys, math, time

# An incredibly simple agent.  All we do is find the closest enemy tank, drive
# towards it, and shoot.  Note that if friendly fire is allowed, you will very
# often kill your own tanks with this code.

#################################################################
# NOTE TO STUDENTS
# This is a starting point for you.  You will need to greatly
# modify this code if you want to do anything useful.  But this
# should help you to know how to interact with BZRC in order to
# get the information you need.
# 
# After starting the bzrflag server, this is one way to start
# this code:
# python agent0.py [hostname] [port]
# 
# Often this translates to something like the following (with the
# port name being printed out by the bzrflag server):
# python agent0.py localhost 49857
#################################################################

class Agent(object):

    def __init__(self, bzrc):
        self.bzrc = bzrc
        self.constants = self.bzrc.get_constants()
        self.commands = []
        self.elapsed_time = 0
        self.time_since_last_shot = 0

    def tick(self, time_diff):
        '''Some time has passed; decide what to do next'''
        # Get information from the BZRC server
        mytanks, othertanks, flags, shots = self.bzrc.get_lots_o_stuff()
        self.mytanks = mytanks
        self.othertanks = othertanks
        self.flags = flags
        self.shots = shots
        self.enemies = [tank for tank in othertanks if tank.color !=
                self.constants['team']]

        # Reset my set of commands (we don't want to run old commands)
        self.commands = []

        self.elapsed_time += time_diff
        self.time_since_last_shot += time_diff

        #print('elapsed time: ' + str(self.elapsed_time)) # DEBUG
        #print('time since last shot: ' + str(self.time_since_last_shot))

        # Decide what to do with each of my tanks
        for bot in mytanks:
            if bot.index == 0:
                print('bot.shots_avail ' + str(bot.shots_avail)) # DEBUG
            self.move(bot, time_diff)

        if self.time_since_last_shot > 2000:
            self.time_since_last_shot = 0
            print('shooting at ' + str(self.elapsed_time))
            for bot in mytanks:
                self.commands.append(Command(bot.index,1,bot.angvel,True))

        # Send the commands to the server
        results = self.bzrc.do_commands(self.commands)

    def move(self, bot, time_diff):
        # at first, just start moving forward        
        if self.elapsed_time == 0:
            self.commands.append(Command(bot.index,1,0,False))
            if bot.index == 0:
                print('commands for bot ' + str(bot.index) + ' speed: 1 angvel: 0 shoot: False') # DEBUG
        
        #if self.elapsed_time % 2000 < 200:
        #    self.commands.append(Command(bot.index,1,0,True))
        #    if bot.index == 0:
        #        print('commands for bot ' + str(bot.index) + ' speed: 1 angvel: 0 shoot: True') # DEBUG


def main():
    # Process CLI arguments.
    try:
        execname, host, port = sys.argv
    except ValueError:
        execname = sys.argv[0]
        print >>sys.stderr, '%s: incorrect number of arguments' % execname
        print >>sys.stderr, 'usage: %s hostname port' % sys.argv[0]
        sys.exit(-1)

    # Connect.
    #bzrc = BZRC(host, int(port), debug=True)
    bzrc = BZRC(host, int(port))

    agent = Agent(bzrc)

    prev_time = time.time()

    # Run the agent
    try:
        while True:
            time_diff = time.time() - prev_time
            agent.tick(time_diff)
    except KeyboardInterrupt:
        print "Exiting due to keyboard interrupt."
        bzrc.close()


if __name__ == '__main__':
    main()

# vim: et sw=4 sts=4

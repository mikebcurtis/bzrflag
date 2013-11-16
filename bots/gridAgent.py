#!/usr/bin/python -tt


#for debug:
#import pdb; pdb.set_trace()



from bzrc import BZRC, Command, Answer
import sys, math, time, random

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

        self.update()
        self.past_position = {}
        self.desired_angle = {}
        self.past_angle_error = {}
        self.moving = {}
        self.consec_not_moving = {}

        # Determine the position of the center of our base (Where to return the flag)
        bases = self.bzrc.get_bases()
        for base in bases:
            if base.color == self.constants['team']:
                self.base = Answer()
                self.base.x = (base.corner1_x+base.corner3_x)/2
                self.base.y = (base.corner1_y+base.corner3_y)/2

        # Constants        
        self.attractive_constant = 5

        #find center point of all tanks
        avg_x = sum(tank.x for tank in self.mytanks) / len(self.mytanks)
        avg_y = sum(tank.y for tank in self.mytanks) / len(self.mytanks)

        # set initial positions of all of the tanks on our team
        for tank in self.mytanks:
                self.past_position[tank.index] = tank.x, tank.y
                self.past_angle_error[tank.index] = 0
                angle_increment = (2 * math.pi) / len(self.mytanks)
                #self.desired_angle[tank.index] = angle_increment * tank.index
                #self.desired_angle[tank.index] = 0 # DEBUG
                self.desired_angle[tank.index] = math.atan2(tank.y - avg_y, tank.x - avg_x)
                self.moving[tank.index] = False
                self.consec_not_moving[tank.index] = 0
            

    def update(self):
        # Get information from the BZRC server
        mytanks, othertanks, flags, shots = self.bzrc.get_lots_o_stuff()
        self.mytanks = mytanks
        

    '''Some time has passed; decide what to do next'''
    def tick(self, time_diff):
        self.update()
        self.commands = []
        
        angle_increment = (2 * math.pi) / len(self.mytanks)
        
        for tank in self.mytanks:
            tank_angle = self.normalize_angle(tank.angle)
            past_x, past_y = self.past_position[tank.index]
            if (tank_angle - self.desired_angle[tank.index])**2 < 0.001:
                #print("Tank " + str(tank.index) + " reached desired angle. current angle = " + str(tank_angle) + " desired angle = " + str(self.desired_angle[tank.index])) # DEBUG
                #self.commands.append(Command(tank.index, 0, 0, False)) # DEBUG
                
                if self.moving[tank.index] == False:
                    # reached desired angle. start moving
                    self.moving[tank.index] = True
                    self.consec_not_moving[tank.index] = 0
                    self.commands.append(Command(tank.index, 1, 0, False))
                elif tank.x - past_x == 0 or tank.y - past_y == 0:
                    self.consec_not_moving[tank.index] += 1
                    print("tank " + str(tank.index) + " consec_not_moving = " + str(self.consec_not_moving[tank.index]))
                    if self.consec_not_moving[tank.index] > 10:
                        print("staaaaapppp!! tank " + str(tank.index) + " reached a consec_not_moving of " + str(self.consec_not_moving[tank.index]))
                        self.commands.append(Command(tank.index,0,0,False))
                else:
                    self.consec_not_moving[tank.index] = 0
                #elif (tank.x - past_x == 0 and tank.y - past_y != 0) or (tank.x - past_x != 0 and tank.y - past_y == 0): # already moving, check if we're stuck
                    
                    # we're stuck. stop the tank and change the angle
                 #   if tank.index == 0:
                 #       print('tank.x ' + str(tank.x) + ' past.x ' + str(past_x))# DEBUG
                 #       print('tank.y ' + str(tank.y) + ' past.y ' + str(past_y))# DEBUG
                 #   self.moving[tank.index] = False
                 #   self.desired_angle[tank.index] = self.normalize_angle(self.desired_angle[tank.index] + math.pi / 2)
                    #self.commands.append(Command(tank.index,0,0,False))
                    #self.reflect_angle(tank)  
            else:
                self.rotate_to_angle(tank, self.desired_angle[tank.index])
        
        results = self.bzrc.do_commands(self.commands)
        
    def angle_between(self, given, angle1, angle2):
        norm = self.normalize_angle(given)
        return norm >= angle1 and norm < angle2
    
    def random_pos(self):
        width = int(self.constants['worldsize'])
        x = random.randrange(width) - width/2
        y = random.randrange(width) - width/2
        return x,y  
        
    def reflect_angle(self,tank):
        tank_angle = self.normalize_angle(tank.angle)
        past_x, past_y = self.past_position[tank.index]
        if tank.x - past_x == 0:
            # find which quadrant you're in
            if self.angle_between(tank_angle,0,math.pi/2) or self.angle_between(tank_angle,math.pi,math.pi * 3/2):
                # angle is in first and third quadrants, add
                self.desired_angle[tank.index] = self.normalize_angle(tank_angle + math.pi/2)
            else:
                # angle is in second and fourth quadrants, subtract
                self.desired_angle[tank.index] = self.normalize_angle(tank_angle - math.pi/2)
        elif tank.y - past_y == 0:
            # find which quadrant you're in
            if self.angle_between(tank_angle,0,math.pi/2) or self.angle_between(tank_angle,math.pi,math.pi * 3/2):
                # angle is in first and third quadrants, subtract
                self.desired_angle[tank.index] = self.normalize_angle(tank_angle - math.pi/2)
            else:
                # angle is in second and fourth quadrants, add
                self.desired_angle[tank.index] = self.normalize_angle(tank_angle + math.pi/2)
        
    def rotate_to_angle(self, bot, target_angle):
        kp = 1
        kd = 1
        relative_angle = self.normalize_angle(target_angle - bot.angle)
        angle_change = relative_angle - self.past_angle_error[bot.index]
        command = Command(bot.index, 0, kp * relative_angle + kd * angle_change, False)
        self.commands.append(command)
        self.past_angle_error[bot.index] = relative_angle
        if bot.index == 0:
            print("bot 0 command angular velocity: " + str(kp * relative_angle + kd * angle_change)) # DEBUG

    def move_to_position(self, bot, target_x, target_y):
        target_angle = math.atan2(target_y, target_x)
        relative_angle = self.normalize_angle(target_angle - bot.angle)
        command = Command(bot.index, 1, relative_angle, False)
        self.commands.append(command)

    def normalize_angle(self, angle):
        '''Make any angle be between +/- pi.'''
        angle -= 2 * math.pi * int (angle / (2 * math.pi))
        if angle <= -math.pi:
            angle += 2 * math.pi
        elif angle > math.pi:
            angle -= 2 * math.pi
        return angle 

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

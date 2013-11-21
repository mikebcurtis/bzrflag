#!/usr/bin/python -tt


#for debug:
#import pdb; pdb.set_trace()



from bzrc import BZRC, Command, Answer
import sys, math, time, random
from grid_filter_gl import *
from numpy import zeros

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
                
        # Visualization
        self.window_size = 800
        init_window(self.window_size,self.window_size);
        self.grid = zeros((self.window_size,self.window_size))

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
            #self.desired_angle[tank.index] = math.pi # DEBUG
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
            self.occgrid_debug(tank)        
            tank_angle = self.normalize_angle(tank.angle)
            past_x, past_y = self.past_position[tank.index]
            x_change = tank.x - past_x
            y_change = tank.y - past_y

            if (tank_angle - self.desired_angle[tank.index])**2 < 0.001: # reached desired angle. start moving                 
                if self.moving[tank.index] == False:
                    self.moving[tank.index] = True
                    self.consec_not_moving[tank.index] = 0
                    self.commands.append(Command(tank.index, 1, 0, False))
                
                elif ((x_change == 0 and (not self.going_vertical(tank_angle))) or (y_change == 0 and (not self.going_horizontal(tank_angle))) or
                        (x_change == 0 and self.going_horizontal(tank_angle)) or (y_change == 0 and self.going_vertical(tank_angle))): # Going horizontal or vertical
                    self.consec_not_moving[tank.index] += 1
                    if self.consec_not_moving[tank.index] > 20:
                        self.commands.append(Command(tank.index, 0, 0, False))
                        self.moving[tank.index] = False
                        self.reflect_angle(tank)
                else:
                    self.consec_not_moving[tank.index] = 0
            else: # Haven't reached our desired angle yet - Keep rotating
                self.rotate_to_angle(tank, self.desired_angle[tank.index])

            self.past_position[tank.index] = tank.x, tank.y
        
        results = self.bzrc.do_commands(self.commands)
        update_grid(self.grid)
        draw_grid()
        
    def occgrid_debug(self, tank):
        top_left, tank_grid = self.bzrc.get_occgrid(tank.index)
        top_left_x = top_left[0] + self.window_size / 2
        top_left_y = top_left[1] + self.window_size / 2
        
        for i in range(0,len(tank_grid) - 1):
            for j in range(0,len(tank_grid[0]) - 1): # assuming all rows are the same size
                window_y = top_left_y - i - 1
                window_x = top_left_x + j - 1
                if window_y >= self.window_size:
                    window_y = self.window_size - 1
                elif window_y < 0:
                    window_y = 0
                if window_x >= self.window_size - 1:
                    window_x = self.window_size - 1
                elif window_x < 0:
                    window_x = 0
                self.grid[window_y][window_x] = tank_grid[i][j]
                #self.grid[top_left_y - i][top_left_x + j] = 1 # DEBUG sensor gives all 1s                

    # Going generally straight left or right
    def going_horizontal(self, angle):
        tolerance = .2
        diff = 0
        if(angle > 0):
            return ((math.pi - angle) <= tolerance) or (angle <= tolerance)
        else:
            return ((math.pi + angle) <= tolerance) or ((0 - angle) <= tolerance)
        
    # Going generally straight up or down
    def going_vertical(self, angle):
        tolerance = .2
        positive_angle = math.fabs(angle)
        if(positive_angle > math.pi/2):
            return ((positive_angle - math.pi/2) <= tolerance)
        else:
            return ((math.pi/2 - positive_angle) <= tolerance)
        
    def angle_between(self, given, smaller_angle, larger_angle):
        angle = self.normalize_angle(given)
        return smaller_angle <= angle and angle < larger_angle
    
    def random_pos(self):
        width = int(self.constants['worldsize'])
        x = random.randrange(width) - width/2
        y = random.randrange(width) - width/2
        return x,y  
    
    # Add or subtract 60* depending on how tank hits a wall    
    def reflect_angle(self,tank):
        tank_angle = self.normalize_angle(tank.angle)
        past_x, past_y = self.past_position[tank.index]

        # Rotate by an angle between 45* and 90*
        angle_to_rotate_by = random.uniform(math.pi/4, math.pi/2)
        #angle_to_rotate_by = math.pi/2

        if tank.x - past_x == 0:
            # Up and Right or Down and Left (Turn Left)
            if self.angle_between(tank_angle, 0, math.pi/2) or self.angle_between(tank_angle, -math.pi, -math.pi/2):
                self.desired_angle[tank.index] = self.normalize_angle(tank_angle + angle_to_rotate_by)
            # Up and Left or Down and Right (Turn Right)
            else:
                self.desired_angle[tank.index] = self.normalize_angle(tank_angle - angle_to_rotate_by)

        elif tank.y - past_y == 0:
            # Up and Right or Down and Left (Turn Right)
            if self.angle_between(tank_angle, 0, math.pi/2) or self.angle_between(tank_angle, -math.pi, -math.pi/2):
                self.desired_angle[tank.index] = self.normalize_angle(tank_angle - angle_to_rotate_by)
            # Up and Left or Down and Right (Turn Left)
            else:
                self.desired_angle[tank.index] = self.normalize_angle(tank_angle + angle_to_rotate_by)
        
    def rotate_to_angle(self, bot, target_angle):
        kp = 1
        kd = 1
        relative_angle = self.normalize_angle(target_angle - bot.angle)
        angle_change = relative_angle - self.past_angle_error[bot.index]
        command = Command(bot.index, 0, kp * relative_angle + kd * angle_change, False)
        self.commands.append(command)
        self.past_angle_error[bot.index] = relative_angle

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

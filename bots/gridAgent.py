#!/usr/bin/python -tt

#for debug:
#import pdb; pdb.set_trace()
from bzrc import BZRC, Command, Answer
import sys, math, time, random, thread
from grid_filter_gl import *
from numpy import zeros, ones

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

#        for thing in self.constants:
#            print (str(thing) + "=" + str(self.constants[thing]))

        self.update()
        self.past_position = {}
        self.desired_angle = {}
        self.past_angle_error = {}
        self.moving = {}
        self.consec_not_moving = {}

        self.WorldDim = int(self.constants['worldsize'])
        init_window(self.WorldDim, self.WorldDim);
        self.angle_tolerance = .4
        self.numTanks = 10
        self.tankSpeed = 1

        '''########################  Likelihoods ####################         
        # For this problem, there are two possible states for each cell: occupied and unoccupied.
        # For each cell, there are three possible observations: hit, no-hit, and no observation.
        # Since we won't update probabilities in the absence of an observation, we will only use
        # the hit or miss observations.
        #
        # We can give names for each likelihood as follows:
        # p(O=hit|S=occupied) = "TrueHit"
        # p(O=hit|S=unoccupied) = "FalseAlarm"
        # p(O=no-hit|S=occupied) = "MissedDetection" = 1-TrueHit
        # p(O=no-hit|S=unoccupied) = "TrueMiss" = 1-FalseAlarm'''

        # The probability that an occupied cell is detected as a hit by the observer.
        self.TrueHit = float(self.constants['truepositive']) 
        # The probability that an unoccupied cell is detected as a hit.
        self.FalseAlarm = 1 - float(self.constants['truenegative'])

        '''########################### CREATE PROBABILITY GRID ###########################
        # Create a data structure that holds the probability that the point
        # specified by the index contains an obstacle.  Initialize it to a
        # probability of 0.25 per each obstacle.'''
        self.p = .25 * ones((self.WorldDim, self.WorldDim))
        self.pCount = zeros((self.WorldDim, self.WorldDim))

        # Determine the position of the center of our base (Where to return the flag)
        bases = self.bzrc.get_bases()
        for base in bases:
            if base.color == self.constants['team']:
                self.base = Answer()
                self.base.x = (base.corner1_x+base.corner3_x)/2
                self.base.y = (base.corner1_y+base.corner3_y)/2

        #find center point of all tanks
        avg_x = sum(tank.x for tank in self.mytanks) / len(self.mytanks)
        avg_y = sum(tank.y for tank in self.mytanks) / len(self.mytanks)

        # set initial positions of all of the tanks on our team
        for tank in self.mytanks:
            self.past_position[tank.index] = tank.x, tank.y
            self.past_angle_error[tank.index] = 0
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
        self.updateGrid()
        self.moveTanks()

    ''' Move each tank '''
    def moveTanks(self):
        for tank in self.mytanks:
            #self.move_based_on_desired_angle(tank) # OLD WAY
            self.move_tank(tank) # NEW WAY = BETTER WAY
            self.past_position[tank.index] = tank.x, tank.y
        
        results = self.bzrc.do_commands(self.commands)

    ''' This has tanks constantly moving, changing direction when necessary '''
    def move_tank(self, tank):
        tank_angle = self.normalize_angle(tank.angle)
        desired_angle = self.desired_angle[tank.index]
        past_x, past_y = self.past_position[tank.index]
        x_change = tank.x - past_x
        y_change = tank.y - past_y

        if (tank_angle - desired_angle)**2 < .001:
            self.commands.append(Command(tank.index, self.tankSpeed, 0, False))                            
        else:
            self.move_with_angle(tank, tank_angle)

        if (((x_change == 0 and (not self.going_vertical(tank_angle))) or 
                  (y_change == 0 and (not self.going_horizontal(tank_angle))) or
                  (x_change == 0 and self.going_horizontal(tank_angle)) or 
                  (y_change == 0 and self.going_vertical(tank_angle))) and
                  tank.index < self.numTanks): # Going horizontal or vertical
                self.reflect_angle(tank)
                tank_angle = self.desired_angle[tank.index]
                self.move_with_angle(tank, tank_angle)

    ''' This stops tanks before rotating them - it has issues with tanks stopping and going '''
    def move_based_on_desired_angle(self, tank):
        tank_angle = self.normalize_angle(tank.angle)
        past_x, past_y = self.past_position[tank.index]
        x_change = tank.x - past_x
        y_change = tank.y - past_y
        
        # reached desired angle. start moving
        if (tank_angle - self.desired_angle[tank.index])**2 < 0.001:
            if self.moving[tank.index] == False:
                self.moving[tank.index] = True
                self.consec_not_moving[tank.index] = 0
                self.commands.append(Command(tank.index, self.tankSpeed, 0, False))
            elif (((x_change == 0 and (not self.going_vertical(tank_angle))) or 
                  (y_change == 0 and (not self.going_horizontal(tank_angle))) or
                  (x_change == 0 and self.going_horizontal(tank_angle)) or 
                  (y_change == 0 and self.going_vertical(tank_angle))) and
                  tank.index < self.numTanks): # Going horizontal or vertical
                self.consec_not_moving[tank.index] += 1
                if self.consec_not_moving[tank.index] > 35:
                    self.commands.append(Command(tank.index, 0, 0, False))
                    self.moving[tank.index] = False
                    self.reflect_angle(tank)
            else:
                self.consec_not_moving[tank.index] = 0
        else: # Haven't reached our desired angle yet - Keep rotating
            self.rotate_to_angle(tank, self.desired_angle[tank.index])

    ''' Update our grid filter '''
    def updateGrid(self):
        for tank in self.mytanks:
            if(tank.index < self.numTanks):
                self.updateWithTank(tank)
        update_grid(self.p)
        draw_grid()

    '''
    THIS IS HOW THE STUPID GRID IS
      BOTTOM L                TOP L
         Y       
    X [[ 0.  0.  0. ...,  0.  0.  0.]
       [ 0.  0.  0. ...,  0.  0.  0.]
       [ 0.  0.  0. ...,  0.  0.  0.]
       ..., 
       [ 1.  1.  1. ...,  1.  1.  1.]
       [ 1.  1.  1. ...,  1.  1.  1.]
       [ 1.  1.  1. ...,  1.  1.  1.]]
    BOTTOMR R               TOP R 
    Update the grid based on the observation of a single tank'''
    def updateWithTank(self, tank):
        bottom_left, tank_grid = self.bzrc.get_occgrid(tank.index)
        # WE ASSUME THAT WE ARE GETTING [X,Y] - WHO KNOWS IF IT REALLY IS
        bottom_left_x = bottom_left[0] + self.WorldDim / 2
        bottom_left_y = bottom_left[1] + self.WorldDim / 2
        
        #print(str(tank_grid))

        # i's are X (row) j's are Y (col)
        for i in range(0,len(tank_grid) - 1):
            for j in range(0,len(tank_grid[0]) - 1): # assuming all rows are the same size
                window_x = bottom_left_x + i
                window_y = bottom_left_y + j

                self.p[self.WorldDim - 1][self.WorldDim - 1] = 0

                if window_y >= self.WorldDim:
                    window_y = self.WorldDim - 1
                elif window_y < 0:
                    window_y = 0

                if window_x >= self.WorldDim - 1:
                    window_x = self.WorldDim - 1
                elif window_x < 0:
                    window_x = 0
                
                if self.p[window_y][window_x] >= .95:
                    self.p[window_y][window_x] = 1 
                elif self.p[window_y][window_x] <= .05:
                    self.p[window_y][window_x] = 0                       
                else:
                    self.p[window_y][window_x] = self.updateProbability(window_y, window_x, tank_grid[i][j]) # Grid Filter Stuff

    '''########################################## UPDATE PROBABILITIES USING BAYES RULE ##########################################'''
    def updateProbability(self, window_y, window_x, tank_grid_value):
         # If we observe a hit
        if tank_grid_value == 1:
            # Recall that p(SensorX,SensorY) is the probability that a cell is occupied
            Bel_Occ = self.TrueHit * self.p[window_y][window_x]
            # So 1-p(SensorX,SensorY) is the probability that a cell is unoccupied
            Bel_Unocc = self.FalseAlarm * (1 - self.p[window_y][window_x])
            # Normalize
            return Bel_Occ / (Bel_Occ + Bel_Unocc)
        else:  # If do not observe a hit 
            # Recall that p(SensorX,SensorY) is the probability that a cell is occupied
            Bel_Occ = (1 - self.TrueHit) * self.p[window_y][window_x]  
		    # Recall that (1-TrueHit) is the MissedDetection likelihood
            # Recall 1-p(SensorX,SensorY) is the probability that a cell is unoccupied
            Bel_Unocc = (1 - self.FalseAlarm) * (1 - self.p[window_y][window_x])  
		    # Recall that (1-FalseAlarm) is the TrueMiss likelihood
	        # Normalize
            return Bel_Occ / (Bel_Occ + Bel_Unocc)

    '''# Going generally straight left or right'''
    def going_horizontal(self, angle):
        diff = 0
        if(angle > 0):
            return ((math.pi - angle) <= self.angle_tolerance) or (angle <= self.angle_tolerance)
        else:
            return ((math.pi + angle) <= self.angle_tolerance) or ((0 - angle) <= self.angle_tolerance)
        
   '''# Going generally straight up or down'''
    def going_vertical(self, angle):
        positive_angle = math.fabs(angle)
        if(positive_angle > math.pi/2):
            return ((positive_angle - math.pi/2) <= self.angle_tolerance)
        else:
            return ((math.pi/2 - positive_angle) <= self.angle_tolerance)

    ''' Tests if an angle is between smaller_angle and lareger_angle'''    
    def angle_between(self, given, smaller_angle, larger_angle):
        angle = self.normalize_angle(given)
        return smaller_angle <= angle and angle < larger_angle

    ''' Get a random position in the world'''    
    def random_pos(self):
        width = int(self.constants['worldsize'])
        x = random.randrange(width) - width/2
        y = random.randrange(width) - width/2
        return x,y  
    
    ''' Change the angle of a tank that has hit a wall '''
    def reflect_angle(self,tank):
        tank_angle = self.normalize_angle(tank.angle)
        past_x, past_y = self.past_position[tank.index]

        # Rotate by an angle between 45* and 90*
        angle_to_rotate_by = random.uniform(math.pi/4, math.pi/2)
        cornerRange = 20

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

    ''' Used to rotate a non-moving tank - OLD WAY '''        
    def rotate_to_angle(self, bot, target_angle):
        kp = 1
        kd = 1
        relative_angle = self.normalize_angle(target_angle - bot.angle)
        angle_change = relative_angle - self.past_angle_error[bot.index]
        command = Command(bot.index, 0, kp * relative_angle + kd * angle_change, False)
        self.commands.append(command)
        self.past_angle_error[bot.index] = relative_angle
    
    ''' Used to rotate a moving tank - NEW WAY = BETTER WAY'''
    def move_with_angle(self, bot, target_angle):
        relative_angle = self.normalize_angle(target_angle - bot.angle)
        command = Command(bot.index, self.tankSpeed, relative_angle, False)
        self.commands.append(command)

    '''Make any angle be between +/- pi.'''
    def normalize_angle(self, angle):
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

#!/usr/bin/python -tt

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
        self.goals = {}

        # Determine the position of the center of our base (Where to return the flag)
        bases = self.bzrc.get_bases()
        for base in bases:
            if base.color == self.constants['team']:
                self.base = Answer()
                self.base.x = (base.corner1_x+base.corner3_x)/2
                self.base.y = (base.corner1_y+base.corner3_y)/2

        # avoid enemies within this radius
        self.enemy_influence_radius = 30
        self.obstacle_influence_radius = 150
        self.obstacle_influence_distance = 30
        
        # Constants        
        self.attractive_constant = 5

        self.enemy_repulsive_constant = 5
        self.enemy_tangential_constant = 10

        self.obstacle_repulsive_constant = 80
        self.obstacle_tangential_constant = 50

        self.obstacles = []
        #self.create_obstacles(self.bzrc.get_obstacles()) # Trevor's original code
        self.obstacles = self.bzrc.get_obstacles()
        #print(str(self.obstacles))# TODO remove DEBUG

        # set initial positions of all of the tanks on our team
	for tank in self.mytanks:
            self.past_position[tank.index] = tank.x, tank.y
            self.goals[tank.index] = None

    def update(self):
        # Get information from the BZRC server
        mytanks, othertanks, flags, shots = self.bzrc.get_lots_o_stuff()
        self.mytanks = mytanks
        self.othertanks = othertanks
        self.flags = flags
        self.shots = shots
        self.enemies = [tank for tank in othertanks if tank.color != self.constants['team']]

    # find the flag closest to each tank and set that as their goal
    def set_flag_goals(self):
        for tank in self.mytanks:
            best = [0,None]
            flag = self.closest_flag(tank)
            if flag:
                self.goals[tank.index] = flag.x, flag.y     
        

    '''Some time has passed; decide what to do next'''
    def tick(self, time_diff):
        self.update()
        self.commands = []

        # Decide what to do with each of my tanks
        for bot in self.mytanks:
            #if(bot.index == 0): # Uncomment this for testing
                dx, dy = self.update_goal(bot)
                self.move_to_position(bot, dx, dy)     
                self.past_position[bot.index] = bot.x, bot.y

        results = self.bzrc.do_commands(self.commands)

    def update_goal(self, bot):
        dx = 0
        dy = 0        
        # ==== STUCK -> MOVE SOME RANDOM DIRECTION (TO GET UNSTUCK) ====
        #if (bot.x, bot.y) == self.past_position[bot.index]:
        #    dx, dy = self.random_pos() 
        #else:
        x, y = self.get_attractive_fields(bot)

        eRX, eRY = self.get_enemy_fields(bot, True)
        eTX, eTY = self.get_enemy_fields(bot, False)   

        oRX, oRY = self.get_obstacle_fields(bot)
        oTX = 0
        oTY = 0
        #oRX, oRY = self.get_obstacle_fields(bot, True)
        #oTX, oTY = self.get_obstacle_fields(bot, False)
 
        #print("X: " + str(x) + " Y: " + str(y))
        #print("eRX: " + str(eRX) + " eRY: " + str(eRY))    
        #print("eTX: " + str(eTX) + " eTY: " + str(eTY))  
        #print("oRX: " + str(oRX) + " oRY: " + str(oRY))      
        #print("oTX: " + str(oTX) + " oTY: " + str(oTY))  
        
        dx = x + eRX + eTX + oRX + oTX
        dy = y + eRY + eTX + oRY + oTY

        #print("dx: " + str(dx) + " dy: " + str(dy))          

        return dx, dy

    def get_attractive_fields(self, bot):
        dx_dy = 0, 0

        # ==== ENEMY FLAG -> BACK TO BASE ====
        if bot.flag != '-':
            dx_dy = (self.base.x - bot.x), (self.base.y - bot.y)
        else:
            # ==== NO FLAG -> GO GET AN ENEMY FLAG ====
            flag = self.closest_flag(bot)
            if flag:
                dx_dy = (flag.x - bot.x), (flag.y - bot.y)
            # ==== ALL FLAGS ARE TAKEN -> HEAD SOME RANDOM DIRECTION ====
            else:
                x, y = self.random_pos()
                dx_dy = (x - bot.x), (y - bot.y)
        x, y = dx_dy
        dx_dy = (self.attractive_constant * x), (self.attractive_constant * y)
        return dx_dy     

    def get_enemy_fields(self, bot, repulsive):
        dx_dy = 0, 0
        
        for enemy in self.enemies:      
            x = 0
            y = 0
            if(repulsive):
                x, y = self.get_repulsive_field(bot, enemy.x, enemy.y, self.enemy_influence_radius, self.enemy_repulsive_constant)
            else:
                x, y = self.get_tangential_field(bot, enemy.x, enemy.y, self.enemy_influence_radius, self.enemy_tangential_constant)
            dx, dy = dx_dy
            dx_dy = (x + dx), (y + dy) 
        return dx_dy

    def get_obstacle_fields(self, bot):
        dx = 0
        dy = 0
        
        for obstacle in self.obstacles:
            for x in range(1,len(obstacle) + 1):
                idx1 = x - 1
                idx2 = x
                if x == len(obstacle):
                    idx2 = 0
                #print("idx1 = " + str(idx1)) # TODO remove DEBUG
                #print("idx2 = " + str(idx2)) # TODO remove DEBUG
                p1 = obstacle[idx1]
                p2 = obstacle[idx2]
                
                if p1[0] >= p2[0]:
                    near_pt_x, near_pt_y = self.get_nearest_point_on_line(p1[0],p1[1],p2[0],p2[1],bot)
                elif p1[0] < p2[0]:
                    near_pt_x, near_pt_y = self.get_nearest_point_on_line(p2[0],p2[1],p1[0],p1[1],bot)
                distance_to_line = math.sqrt((near_pt_x - bot.x)**2 + (near_pt_y - bot.y)**2)
                if distance_to_line <= self.obstacle_influence_distance:
                    #print("bot at (" + str(bot.x) + ", " + str(bot.y) + ") is " + str(distance_to_line) + " from the line (" + str(p1) + ", " + str(p2) + ") at the point (" + str(near_pt_x) + ", " + str(near_pt_y) + ")") # TODO remove DEBUG
                    angle = math.atan2(near_pt_y - bot.y, near_pt_x - bot.x)
                    dx += -1 * self.obstacle_repulsive_constant * (self.obstacle_influence_distance - distance_to_line) * math.cos(angle)
                    dy += -1 * self.obstacle_repulsive_constant * (self.obstacle_influence_distance - distance_to_line) * math.sin(angle)
                    dx += -1 * self.obstacle_tangential_constant * (self.obstacle_influence_distance - distance_to_line) * math.cos(angle + 90)
                    dy += -1 * self.obstacle_tangential_constant * (self.obstacle_influence_distance - distance_to_line) * math.sin(angle + 90)
                #else:
                    #print("too far from line")
        return dx, dy
                

    def get_nearest_point_on_line(self, p1_x, p1_y, p2_x, p2_y, bot):
        '''Get the nearest point on the line formed by p1 and p2 to the bot.'''
        # math taken from Building Interactive Systems by Dr. Olsen, pg 251
        # L = A + t(B - A)
        # t = -(A.x - M.x)(B.x - A.x) - (A.y - M.y)(B.y - A.y) / (B.x - A.x)**2 + (B.y - A.y)**2
        t = ((-1 * (p1_x - bot.x) * (p2_x - p1_x)) - ((p1_y - bot.y) * (p2_y - p1_y))) / ((p2_x - p1_x)**2 + (p2_y - p1_y)**2)
        
        # build the nearest point on the line to the tank, A + t(B - A)
        near_pt_x = p1_x + (t * (p2_x - p1_x))
        near_pt_y = p1_y + (t * (p2_y - p1_y))
        
        #print('bot at ' + str((bot.x, bot.y)) + ' is nearest to line ' + str((p1_x, p1_y)) + " to " + str((p2_x, p2_y)) + " at " + str(near_pt)) # TODO remove DEBUG
        
        # make sure no only consider the line between the two given line segments
        if near_pt_x > max([p1_x, p2_x]):
            near_pt_x = max([p1_x, p2_x])
        elif near_pt_x < min([p1_x, p2_x]):
            near_pt_x = min([p1_x, p2_x])
            
        if near_pt_y > max([p1_y, p2_y]):
            near_pt_y = max([p1_y, p2_y])
        elif near_pt_y < min([p1_y, p2_y]):
            near_pt_y = min([p1_y, p2_y])
            
        return (near_pt_x, near_pt_y)

    #def get_obstacle_fields(self, bot, repulsive):
    #    dx_dy = 0, 0
    #
    #    for obstacle in self.obstacles:
    #        center_x, center_y = obstacle
    #        x = 0
    #        y = 0
    #        if(repulsive):
    #            x, y = self.get_repulsive_field(bot, center_x, center_y, self.obstacle_influence_radius, self.obstacle_repulsive_constant)
    #        else:
    #            x, y = self.get_tangential_field(bot, center_x, center_y, self.obstacle_influence_radius, self.obstacle_tangential_constant)
    #        dx, dy = dx_dy
    #        dx_dy = (x + dx), (y + dy)
    #    return dx_dy

    def get_repulsive_field(self, bot, x, y, radius, constant):
        dist = math.sqrt((x - bot.x)**2 + (y - bot.y)**2)
        angle = math.atan2(y - bot.y, x - bot.x)
        if dist < radius:
            # TODO - Decide which way to rotate depending on what part of the object you are headed towards?
            dx = -1 * ((self.obstacle_influence_radius - dist) * math.cos(angle))
            dy = -1 * ((self.obstacle_influence_radius - dist) * math.sin(angle))
            return (constant * dx), (constant * dy)
        return 0, 0
        
    def get_tangential_field(self, bot, x, y, radius, constant):
        dist = math.sqrt((x - bot.x)**2 + (y - bot.y)**2)
        angle = math.atan2(y - bot.y, x - bot.x)
        if dist < radius:
            # TODO - decide which way to turn?
            dx = ((self.enemy_influence_radius - dist) * math.cos(90 + angle))
            dy = ((self.enemy_influence_radius - dist) * math.sin(90 + angle)) 
            return (constant * dx), (constant * dy)     
        return 0, 0            
      
    def closest_flag(self, bot):
        best = None
        for flag in self.flags:
            if flag.color == self.constants['team']:
                continue
            if flag.poss_color != 'none':
                continue
            # TODO temporary
            #if flag.color != 'blue':
            #    continue
            dist = math.sqrt((flag.x - bot.x)**2 + (flag.y - bot.y)**2)
            if not best or dist < best[0]:
                best = [dist, flag]
        if best:
            return best[1]  
    
    def random_pos(self):
        width = int(self.constants['worldsize'])
        x = random.randrange(width) - width/2
        y = random.randrange(width) - width/2
        return x,y          

    def return_to_base(self, bot):
        self.move_to_position(bot, self.base.x, self.base.y)

    def attack_enemies(self, bot):
        '''Find the closest enemy and chase it, shooting as you go'''
        best_enemy = None
        best_dist = 2 * float(self.constants['worldsize'])

        for enemy in self.enemies:
            if enemy.status != 'alive':
                continue
            dist = math.sqrt((enemy.x - bot.x)**2 + (enemy.y - bot.y)**2)
            if dist < best_dist:
                best_dist = dist
                best_enemy = enemy

        if best_enemy is None:
            command = Command(bot.index, 0, 0, False)
            self.commands.append(command)
        else:
            self.move_to_position(bot, best_enemy.x, best_enemy.y)

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

    # Calculate what would be the center of each obstacle and store those as tuples in obstacles list
    def create_obstacles(self, obstacles):       
        for obstacle in obstacles:
            center_x = 0
            center_y = 0
            i = 0

            for corner in obstacle:
                x, y = corner
                center_x += x
                center_y += y  
                i += 1
            center_x /= i
            center_y /= i
            
            center = center_x, center_y
            self.obstacles.append(center)  

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

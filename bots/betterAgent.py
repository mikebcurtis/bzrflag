#!/usr/bin/python -tt

from bzrc import BZRC, Command, Answer
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
        bases = self.bzrc.get_bases()
        for base in bases:
            if base.color == self.constants['team']:
                self.base = Answer()
                self.base.x = (base.corner1_x+base.corner3_x)/2
                self.base.y = (base.corner1_y+base.corner3_y)/2

    def tick(self, time_diff):
        '''Some time has passed; decide what to do next'''
        # Get information from the BZRC server
        mytanks, othertanks, flags, shots = self.bzrc.get_lots_o_stuff()
        self.mytanks = mytanks
        self.othertanks = othertanks
        self.flags = flags
        self.shots = shots
        self.enemies = [tank for tank in othertanks if tank.color != self.constants['team']]

        # Reset my set of commands (we don't want to run old commands)
        self.commands = []

        # Decide what to do with each of my tanks
        for bot in mytanks:
            if bot.flag == '-':
                self.run_to_flag(bot)
            else:
                self.return_to_base(bot)

        # Send the commands to the server
        results = self.bzrc.do_commands(self.commands)

    def run_to_flag(self, bot):
        best_flag = None
        best_dist = 2 * float(self.constants['worldsize'])

        for flag in self.flags:
            # if one of our teammates has the flag, don't swarm them            
            if flag.poss_color == self.constants['team'] or flag.color == self.constants['team']:
                continue
            dist = math.sqrt((flag.x - bot.x)**2 + (flag.y - bot.y)**2)
            if dist < best_dist:
                best_dist = dist
                best_flag = flag

            if best_flag is None:
                command = Command(bot.index, 0, 0, False)
                self.commands.append(command)
            else:
                self.move_to_position(bot, best_flag.x, best_flag.y)            

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
        target_angle = math.atan2(target_y - bot.y,
                target_x - bot.x)
        if target_angle < 0:
            target_angle += 2 * math.pi
        #relative_angle = self.normalize_angle(target_angle - bot.angle)
        relative_angle = self.avoid_obstacles(bot, target_angle - bot.angle)
        #angle = self.avoid_obstacles(bot,angle)
        command = Command(bot.index, 1, 2 * relative_angle, False)
        self.commands.append(command)

    def normalize_angle(self, angle):
        '''Make any angle be between +/- pi.'''
        angle -= 2 * math.pi * int (angle / (2 * math.pi))
        if angle <= -math.pi:
            angle += 2 * math.pi
        elif angle > math.pi:
            angle -= 2 * math.pi
        return angle

    # goal_angle is the angle we need to rotate the tank to point towards the goal
    def avoid_obstacles(self, bot, goal_angle):
        '''Returns the angle the tank should use to avoid obstacles, calculated as the sum of the effects of a repulsive and tangential field eminating from every obstacle on the given angle.'''
        sum_angles = goal_angle
        
        # avoid enemies
        enemy_influence_radius = 30 # do not consider enemies outside the radius
        for enemy in self.enemies:
            dist = math.sqrt((enemy.x - bot.x)**2 + (enemy.y - bot.y)**2)
            if dist < enemy_influence_radius:
                enemy_angle = math.atan2(enemy.y - bot.y, enemy.x - bot.x)
                if enemy_angle < 0:
                    enemy_angle += 2 * math.pi
                sum_angles += enemy_angle + math.pi # oppositeangle
                
            
        # avoid rocks
        #obstacle_influence_radius = 20 # do not consider obstacles outside the radius
        #for obstacle in obstacles:
        #if sum_angles == goal_angle:
        #    return normalize_angle(goal_angle)
        
        #return normalize_angle(sum_angles / self.enemies.len + 1)
        return self.normalize_angle(sum_angles)    

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

#!/usr/bin/env python
'''This is a demo on how to use Gnuplot for potential fields.  We've
intentionally avoided "giving it all away."
'''

from __future__ import division
from itertools import cycle
from bzrc import *
try:
    from numpy import linspace
except ImportError:
    # This is stolen from numpy.  If numpy is installed, you don't
    # need this:
    def linspace(start, stop, num=50, endpoint=True, retstep=False):
        """Return evenly spaced numbers.

        Return num evenly spaced samples from start to stop.  If
        endpoint is True, the last sample is stop. If retstep is
        True then return the step value used.
        """
        num = int(num)
        if num <= 0:
            return []
        if endpoint:
            if num == 1:
                return [float(start)]
            step = (stop-start)/float((num-1))
            y = [x * step + start for x in xrange(0, num - 1)]
            y.append(stop)
        else:
            step = (stop-start)/float(num)
            y = [x * step + start for x in xrange(0, num)]
        if retstep:
            return y, step
        else:
            return y
            
class PFieldPlotter(BZRC):

    def __init__(self):

        ########################################################################
        # Constants

        # Output file:
        self.FILENAME = 'fields.gpi'
        # Size of the world (one of the "constants" in bzflag):
        self.WORLDSIZE = 800
        # How many samples to take along each dimension:
        self.SAMPLES = 25
        # Change spacing by changing the relative length of the vectors.  It looks
        # like scaling by 0.75 is pretty good, but this is adjustable:
        self.VEC_LEN = 0.75 * self.WORLDSIZE / self.SAMPLES
        # Animation parameters:
        self.ANIMATION_MIN = 0
        self.ANIMATION_MAX = 500
        self.ANIMATION_FRAMES = 50

    ########################################################################
    # Overridden BZRF functions
    def get_constants(self):
        return {'team': 'red', 'worldsize': self.WORLDSIZE}
        
    def get_bases(self):
        return []
    
    def get_lots_o_stuff(self):
        return self.get_mytanks(), self.get_enemy_tanks(), self.get_flags(), None
    
    def do_commands(self, commands):
        #self.plotfield(commands)
        return
    
    ########################################################################
    # Trick the Agent Functions
    
    def get_mytanks(self):
        '''Trick the agent to thinking there is a tank at every point where we want to draw a vector arrow.'''
        separation = self.WORLDSIZE / self.SAMPLES
        end = self.WORLDSIZE / 2 - separation / 2
        start = -end
        
        points = ((x, y) for x in linspace(start, end, self.SAMPLES)
                             for y in linspace(start, end, self.SAMPLES))
        
        self.fake_tanks = []
        
        idx = 0                     
        for coordinate in points:
            # make a fake tank for every coordinate
            tank = Answer()
            tank.index = idx
            tank.color = 'red'
            #tank.callsign = line[2]
            #tank.status = line[3]
            #tank.shots_avail = int(line[4])
            #tank.time_to_reload = float(line[5])
            tank.flag = '-'
            tank.x, tank.y = coordinate
            tank.angle = 0
            #tank.vx = float(line[10])
            #tank.vy = float(line[11])
            tank.angvel = 0
            self.fake_tanks.append(tank)
            idx += 1
            
        return self.fake_tanks

            
    def get_enemy_tanks(self):
        '''Place fake enemies on the field to show potential fields that apply to enemies.'''
        self.enemies = []
        
        tank = Answer()
        #tank.callsign = line[1]
        tank.color = 'enemy'
        #tank.status = line[3]
        tank.flag = '-'
        tank.x = 100
        tank.y = 100
        #tank.angle = float(line[7])
        self.enemies.append(tank)
        
        tank2 = Answer()
        tank2.color = 'enemy'
        tank2.flag = '-'
        tank2.x = 50 
        tank2.y = 50
        self.enemies.append(tank2)
        
        #return self.enemies
        return [] # TODO change this, just debugging obstacles
        
    def get_flags(self):
        '''This will place a goal that should show attractive potential fields.'''
        flags = []
        
        flag = Answer()
        flag.color = 'blue'
        flag.poss_color = 'none'
        flag.x = 400
        flag.y = -400
        flags.append(flag)   
        
        return flags  
        
    def get_obstacles(self):
        self.obstacles = [((0, 0), (-200, 0), (-200,-50), (0,-50), (0, -250), (50, -250), (50, -50), (250, -50), (250, 0), (50, 0), (50, 200), (0, 200)), ((150,150),(350,350),(300,222))]
        return self.obstacles
            
    ########################################################################
    # Helper Functions

    def gpi_point(self, x, y, vec_x, vec_y):
        '''Create the centered gpi data point (4-tuple) for a position and
        vector.  The vectors are expected to be less than 1 in magnitude,
        and larger values will be scaled down.'''
        r = (vec_x ** 2 + vec_y ** 2) ** 0.5
        if r > 1:
            vec_x /= r
            vec_y /= r
        return (x - vec_x * self.VEC_LEN / 2, y - vec_y * self.VEC_LEN / 2,
                vec_x * self.VEC_LEN, vec_y * self.VEC_LEN)

    def gnuplot_header(self, minimum, maximum):
        '''Return a string that has all of the gnuplot sets and unsets.'''
        s = ''
        s += 'set xrange [%s: %s]\n' % (minimum, maximum)
        s += 'set yrange [%s: %s]\n' % (minimum, maximum)
        # The key is just clutter.  Get rid of it:
        s += 'unset key\n'
        # Make sure the figure is square since the world is square:
        s += 'set size square\n'
        # Add a pretty title (optional):
        s += "set title 'Potential Fields'\n"
        return s

    def draw_line(self, p1, p2):
        '''Return a string to tell Gnuplot to draw a line from point p1 to
        point p2 in the form of a set command.'''
        x1, y1 = p1
        x2, y2 = p2
        return 'set arrow from %s, %s to %s, %s nohead lt 3\n' % (x1, y1, x2, y2)

    def draw_obstacles(self, obstacles):
        '''Return a string which tells Gnuplot to draw all of the obstacles.'''
        s = 'unset arrow\n'

        for obs in obstacles:
            last_point = obs[0]
            for cur_point in obs[1:]:
                s += self.draw_line(last_point, cur_point)
                last_point = cur_point
            s += self.draw_line(last_point, obs[0])
        return s

    def plot_field(self, agent):
        '''Return a Gnuplot command to plot a field.'''
        s = self.draw_obstacles(self.obstacles)
        s += '\n\n'
        
        s += "plot '-' with vectors head\n"
        
        for fake_tank in self.fake_tanks:
            dx, dy = agent.update_goal(fake_tank)
            plotvalues = self.gpi_point(fake_tank.x, fake_tank.y, fake_tank.x + dx, fake_tank.y + dy)
            x1, y1, x2, y2 = plotvalues
            s += '%s %s %s %s\n' % (x1, y1, x2, y2)            

        s += 'e\n'
        return s

########################################################################
# Animate a changing field, if the Python Gnuplot library is present

if __name__ == '__main__':
    from betterAgent import *
    from bzrc import *
    
    try:
        from Gnuplot import GnuplotProcess
    except ImportError:
        print "Sorry.  You don't have the Gnuplot module installed."
        import sys
        sys.exit(-1)

    #forward_list = list(linspace(ANIMATION_MIN, ANIMATION_MAX, ANIMATION_FRAMES/2))
    #backward_list = list(linspace(ANIMATION_MAX, ANIMATION_MIN, ANIMATION_FRAMES/2))
    #anim_points = forward_list + backward_list
    plotter = PFieldPlotter()
    agent = Agent(plotter)
    agent.update()
    
    headers = plotter.gnuplot_header(-plotter.WORLDSIZE / 2, plotter.WORLDSIZE / 2)
    vectors = plotter.plot_field(agent)
    
    gp = GnuplotProcess(persist=True)
    gp.write(headers)
    gp.write(vectors)
    
    # animate
    #for scale in cycle(anim_points):
    #    field_function = generate_field_function(scale)
    #    gp.write(plot_field(field_function))
    
    outfile = open('fields.gpi', 'w')
    print >>outfile, headers
    print >>outfile, vectors

# vim: et sw=4 sts=4

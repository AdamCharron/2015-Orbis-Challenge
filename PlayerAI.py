from PythonClientAPI.libs.Game.Enums import *
from PythonClientAPI.libs.Game.MapOutOfBoundsException import *

'''
    In static_array:
    0 - empty
    1 - wall (same as dead turret)
    2 - turret (alive)
    3 - shield
    4 - teleport
    5 - laser (powerup)
    
    In dynamic array:
    7 - laser (from turret)
    8 - bullet
    9 - opponent
    
    Direction:
                   0=Up
                   1=Down
                   2=Left
                   3=Right
                   
            '''
    

class PlayerAI:
    def __init__(self):
        # Initialize any objects or variables you need here.
        self.blockers = [1,2,7,8,9]
        self.powerups = [3,4,5]
        self.n = 5 # scanning area = 2n+1 in all directions, centered around self
        self.threats = [1,7,8,9]

    def get_move(self, gameboard, player, opponent):
        # Write your AI here.
        self.player = player
        if gameboard.current_turn == 0:
            self.create_static_array(gameboard)
        else:
            self.update_static_array(gameboard) # Run every turn to see if statics have changed
            
        pose = (player.x, player.y, self.direction(player))
        opponent_pose = (opponent.x, opponent.y, self.direction(opponent))
        
        return self.scan_vicinity(pose, opponent_pose, gameboard)
        
        
    def direction(self, directional_object):
        if directional_object.direction == Direction.UP:
            return 0
        elif directional_object.direction == Direction.DOWN:
            return 1
        elif directional_object.direction == Direction.LEFT:
            return 2
        else:
            return 3
        
    def wraparound_range(self, start, finish, direction):
        '''direction = 0,1: vertical
           direction = 2,3: horizontal'''
        maxx = self.maxx
        maxy = self.maxy
        retlist = []
        if direction==2 or direction==3:
            if finish > maxx:
                i = 0
                while True:
                    j = start + i
                    if j == finish:
                        break
                    if j >= maxx:
                        j -= maxx
                    retlist.append(j)
                    i += 1
            elif start < maxx:
                i = 0
                while True:
                    j = start + i
                    if j == (finish):
                        break
                    if j < 0:
                        j += maxx
                    retlist.append(j)
                    i += 1
            else:
                retlist = range(start, finish)
            return retlist
        if direction==0 or direction==1:
            if finish > maxy:
                i = 0
                while True:
                    j = start + i
                    if j == finish:
                        break
                    if j >= maxy:
                        j -= maxy
                    retlist.append(j)
                    i += 1
            elif start < maxy:
                i = 0
                while True:
                    j = start + i
                    if j == (finish):
                        break
                    if j < 0:
                        j += maxy
                    retlist.append(j)
                    i += 1
            else:
                retlist = range(start, finish)
            return retlist

            
    def update_static_array(self,gameboard): # Run once every turn
        '''Updates semi-static objects (turrets, power_ups)'''
        diff = set(self.power_ups) - set(gameboard.power_ups) # Powerups that no longer exist
        for element in diff:
            self.static_array[element.x][element.y] = 0
            
        diff = set(self.turrets) - set(gameboard.turrets)
        for element in diff:
            self.static_array[element.x][element.y] = 0

    def scan_vicinity(self, pose, opponent_pose, gameboard):
        factor = 2

        opponent_time = self.minimum_time_opponent_threat(opponent_pose, (pose[0], pose[1]), gameboard)
        line = self.check_line_of_sight((pose[0], pose[1]), (opponent_pose[0], opponent_pose[1]))
        if (opponent_time > 3):
            if not line:
                if ((pose[0] == opponent_pose[0]) and (line[0][0]%2 > 1)) or ((pose[1] == opponent_pose[1]) and (line[0][0]%2 < 2)):
                    return Move.SHOOT
        
        xbounds = (pose[0]-self.n,pose[0]+self.n)
        ybounds = (pose[1]-self.n,pose[1]+self.n)
        xrang = self.wraparound_range(xbounds[0],xbounds[1],2)
        yrang = self.wraparound_range(ybounds[0],ybounds[1],0)
        self.dynamic_array = [row[:] for row in self.static_array]
        danger_rating = [[0]*len(yrang) for row in range(len(xrang))]
        bullets = []
        for element in gameboard.bullets:
            if element.x in xrang:
                if element.y in yrang:
                    bullets.append(element)
                    self.dynamic_array[element.x][element.y] = 8
        self.dynamic_array[opponent_pose[0]][opponent_pose[1]] = 9
        
        threats = [] # List of tuples (x,y,threat_num)
        
        # Scan for initial threats
        min_i = pose[0]
        min_j = pose[1]
        for i in xrang:
            for j in yrang:
                if self.dynamic_array[i][j] in self.threats:
                    threats.append((i,j,self.dynamic_array[i][j]))
                    danger_rating[i][j] = -99
                    if self.dynamic_array[i][j] == 8:
                        temp = -(self.turns_until_a_bullet_hits_you((player.x, player.y), (i,j), gameboard))
                        if temp <= 0:
                            danger_rating[i][j] = factor*max(temp, danger_rating[i][j])
                    if self.dynamic_array[i][j] == 9:
                        temp = -self.minimum_time_opponent_threat(opponent_pose, (pose[0], pose[1]), gameboard)
                        if temp <= 0:
                            danger_rating[i][j] = factor*max(temp, danger_rating[i][j])
                    if self.dynamic_array[i][j] == 7:
                        temp = -self.turns_until_a_turret_hits_you(i, j, gameboard, 0)
                        if temp <= 0:
                            danger_rating[i][j] = factor*max(temp, danger_rating[i][j])

                if danger_rating[i][j] < danger_rating[min_i][min_j]:
                    min_i = i
                    min_j = j
                elif (danger_rating[i][j] == danger_rating[min_i][min_j]) and (self.dynamic_array[i][j] >= 3) and (self.dynamic_array[i][j] <= 5):
                    # Preferrably move to the safest power-up
                    min_i = i
                    min_j = j

        # Use shield if available - it is needed
        if (danger_rating[min_i][min_j] == 0) or (danger_rating[min_i][min_j] == 1):
            if player.shield_count > 0:
                return Move.SHIELD

        # Shoot turret
        if (danger_rating[min_i][min_j] < -2) and (((pose[0] == opponent_pose[0]) and line[0][0]%2 > 1) or ((pose[1] == opponent_pose[1]) and line[0][0]%2 < 2)):
            return Move.SHOOT

        # Move to some point
        sequence = self.minimum_path(pose, opponent_pose, gameboard)
        if not sequence is None:
            key = self.sequence_interpreter(sequence)
            return key
        else:
            return Move.SHOOT
                
                
        '''Return values for :
Move.FACE_UP
Move.FACE_DOWN
Move.FACE_LEFT
Move.FACE_RIGHT
Move.NONE
Move.SHOOT
Move.FORWARD
Move.SHIELD
Move.LASER
Move.TELEPORT_0
Move.TELEPORT_1
Move.TELEPORT_2
Move.TELEPORT_3
Move.TELEPORT_4
Move.TELEPORT_5'''
                
    def check_line_of_sight(self, point, target):
        '''Returns list of tuples containing (direction, distance)
        Direction:
                   0=Up
                   1=Down
                   2=Left
                   3=Right'''
        
        retlist = []
        
        if (point[1]==target[1]):
            # Given that y's are aligned, check for line of sight
            blocks = 0
            i = point[0]
            distance = 0
            # First travel right
            while True: # Cannot iterate using range because wraparound
                i += 1
                distance += 1
                if i == self.maxx: # Wraparound
                    i = 0
                if (i,point[1]) == target:
                    break # Clear line of sight found
                if self.static_array[i][point[1]] in self.blockers:
                    blocks = 1 # Wall or turret in the way
                    break
            if blocks == 0:
                retlist.append((3,distance))
            # Now check for left
            blocks = 0
            i = point[0]
            distance = 0
            # Traveling left
            while True: # Cannot iterate using range because wraparound
                i -= 1
                distance += 1
                if i == -1: # Wraparound
                    i = self.maxx - 1
                if (i,point[1]) == target:
                    break # Clear line of sight found
                if self.static_array[i][point[1]] in self.blockers:
                    blocks = 1 # Wall or turret in the way
                    break
            if blocks == 0:
                retlist.append((2,distance))
            
            return retlist
        elif (point[0]==target[0]):
            # (point[0]==target[0])
            blocks = 0
            j = point[1]
            distance = 0
            # First travel up
            while True: # Cannot iterate using range because wraparound
                #print("Up")
                j -= 1
                distance += 1
                if j == -1: # Wraparound
                    j = self.maxy - 1
                if (point[0],j) == target:
                    break # Clear line of sight found
                if self.static_array[point[0]][j] in self.blockers:
                    blocks = 1 # Wall or turret in the way
                    break
            if blocks == 0:
                retlist.append((0,distance))
            
            # Now check for down
            blocks = 0
            j = point[1]
            distance = 0
            
            while True: # Cannot iterate using range because wraparound
                j += 1
                distance += 1
                if j == self.maxy: # Wraparound
                    j = 0
                if (point[0],j) == target:
                    break # Clear line of sight found
                if self.static_array[point[0]][j] in self.blockers:
                    blocks = 1 # Wall or turret in the way
                    break
            if blocks == 0:
                retlist.append((1,distance))
            
            return retlist
        return retlist
        
        
    def create_static_array(self, gameboard):
        '''
        0 - empty
        1 - wall (same as dead turret)
        2 - turret (alive)
        3 - shield
        4 - teleport
        5 - laser
        '''
        x = gameboard.width
        y = gameboard.height
        
        minimum = min(x,y)
        if (2*self.n + 1)<minimum:
            self.n = (minimum - 1)//2
    
        self.static_array = [[0]*y for row in range(x)]
        
        self.maxx = x
        self.maxy = y
    
        self.add_walls_to_static_array(gameboard)
        self.add_turrets_to_static_array(gameboard)
        self.add_power_ups_to_static_array(gameboard)
        
        return
    
    
    def add_walls_to_static_array(self, gameboard):
        for i in range(len(gameboard.walls)):
            x_coord = gameboard.walls[i].x
            y_coord = gameboard.walls[i].y
            self.static_array[x_coord][y_coord] = 1
    
        return 
    
    
    def add_turrets_to_static_array(self, gameboard):
        self.turrets = gameboard.turrets
        for i in range(len(gameboard.turrets)):
            x_coord = gameboard.turrets[i].x
            y_coord = gameboard.turrets[i].y
            self.static_array[x_coord][y_coord] = 2
    
        return 
    
    
    def add_power_ups_to_static_array(self, gameboard):
        self.power_ups = gameboard.power_ups
        for i in range(len(gameboard.power_ups)):
            x_coord = gameboard.power_ups[i].x
            y_coord = gameboard.power_ups[i].y
    
            if gameboard.power_up_at_tile[x_coord][y_coord].power_up_type == PowerUpTypes.SHIELD:
                self.static_array[x_coord][y_coord] = 3
            elif gameboard.power_up_at_tile[x_coord][y_coord].power_up_type == PowerUpTypes.TELEPORT:
                self.static_array[x_coord][y_coord] = 4
            else:
                self.static_array[x_coord][y_coord] = 5
    
        return
        
        
    def turns_until_a_turret_hits_you(self, x, y, gameboard, turns_ahead):
        '''
        Takes in the coordinate value of the turret you are looking at
        Outputs the number of turns remaining until the inputted turret can hit you (assume remain stationary)
        If it can't hit you where you are, returns -1
        If it is hitting you, return 0
        '''
        return 0
        player = self.player
        
        #Turn 1 it begins running this function, so turn = 0 should never be a factor
        sightline = self.check_line_of_sight((player.x, player.y), (x, y))
        if len(sightline) <= 0:
            return -1
        for i in range(len(sightline)):
            if (sightline[i][1] <= 4):
                turns = (gameboard.current_turn + turns_ahead) % (gameboard.turret_at_tile[x][y].fire_time + gameboard.turret_at_tile[x][y].cooldown_time)
                if (turns <= gameboard.turret_at_tile[x][y].fire_time) or (turns == 0):
                    return 0
                else:
                    return turns
        return -1
        
        
    def turns_until_a_bullet_hits_you(self, player_pos, bullet_pos, gameboard):
        '''
        Takes in the coordinates of the bullet you are looking at
        Outputs the number of turns remaining until the inputted turret can hit you (assume remain stationary)
        If it can't hit you where you are, returns -1
        If it is hitting you, return 0
        '''
        
        #Arbitrary high number that will get overwritten by the actual turns value if needed, or return -1 if no collision risk
        turns = 99
        
        #Turn 1 it begins running this function, so turn = 0 should never be a factor
        sightline = self.check_line_of_sight((player_pos[0], player_pos[1]), (bullet_pos[0], bullet_pos[1]))
        for i in range(len(sightline)):
            if (sightline[i][1] <= 4):
                if ((player.x == x) and gameboard.bullets_at_tile[bullet_pos[0]][bullet_pos[1]].direction == Direction.DOWN) or \
                   ((player.x == x) and gameboard.bullets_at_tile[bullet_pos[0]][bullet_pos[1]].direction == Direction.UP) or \
                   ((player.y == y) and gameboard.bullets_at_tile[bullet_pos[0]][bullet_pos[1]].direction == Direction.RIGHT) or \
                   ((player.y == y) and gameboard.bullets_at_tile[bullet_pos[0]][bullet_pos[1]].direction == Direction.LEFT):
                
                    if turns > sightline[i][1]:
                        turns = sightline[i][1]
                    return turns
        return -1
        
    def farthest_sight(self, position,direction):
        ''' Given position and direction, how far can you see (non-wall/turret) in that direction?
            Return -1 if no wall anywhere'''
        distance = 0
        destination = (-1, -1)
        if direction==0:
            x = position(0)
            while True:
                y = position[1] - distance
                if (y <= -2*self.maxy):
                    break                
                if y<0:
                    y+=self.maxy
                if self.static_array[x][y] not in self.blockers:
                    distance += 1
                elif (x,y) == position and distance>0:  # Has wrapped around all the way
                    distance = -1
                    break
                else:
                    if y==0:
                        y = self.maxy - 1
                    else:
                        y -= 1
                    destination = (x, y)
                    break # Wall hit
        elif direction==1:
            x = position[0]
            while True:
                y = position[1] + distance
                if (y >= 2*self.maxy):
                    break
                if y>=self.maxy:
                    y-=self.maxy
                if self.static_array[x][y] not in self.blockers:
                    distance += 1
                elif (x,y) == position and distance>0:
                    distance = -1
                    break
                else:
                    if y==(self.maxy - 1):
                        y = 0
                    else:
                        y += 1
                    destination = (x, y)
                    break
        elif direction==2:
            y = position[1]
            while True:
                x = position[0] - distance
                if (x <= -2*self.maxx):
                    break
                if x<0:
                    x+=self.maxx
                if self.static_array[x][y] not in self.blockers:
                    distance += 1
                elif (x,y) == position and distance>0:
                    distance = -1
                    break
                else:
                    if x==0:
                        x = self.maxx - 1
                    else:
                        x -= 1
                    destination = (x, y)
                    break
        elif direction==3:
            y = position[1]
            if y>=self.maxy:
                y-=self.maxy
            if y<0:
                y+=self.maxy
            while True:
                x = position[0] + distance
                if (x >= 2*self.maxx):
                    break
                if x>=self.maxx:
                    x-=self.maxx
                if x<0:
                    x+=self.maxx
                if self.static_array[x][y] not in self.blockers:
                    distance += 1
                elif (x,y) == position and distance>0:
                    distance = -1
                    break
                else:
                    if x==(self.maxx - 1):
                        x = 0
                    else:
                        x += 1
                    destination = (x, y)
                    break
        return distance, destination
            
        
    def minimum_time_opponent_threat(self, pose, position, gameboard):
        ''' 
        minimum time it takes for the opponent at pose to align with us, aim, shoot, and hit us given we're at position
        assume clean path (through laser but not wall) directly towards us
        Laser > bullets
        pose: (position.x, position.y,direction)
        position: (position.x, position.y)
        if direction=-1, doesn't matter
        '''
        if pose[0]>position[0]:
            # Opponent further right
            rdistance, rdest = self.farthest_sight(position, 3)
            right_placement = position[0]+rdistance
            
            if right_placement >= self.maxx:
                right_placement -= self.maxx
            
            if right_placement > pose[0] or rdistance==-1:
                rdest = (pose[0], position[1], 2) # Opponent is seeking to be in your y but the their x, facing left. Also adding orientation
            else:
                rdest = (rdest[0], rdest[1], 2)
            if rdistance == -1:
                rdistance = position[0] - pose[0]
                if rdistance < 0:
                    rdistance += self.maxx
                    
            temp = self.minimum_path(pose, rdest, gameboard)
            horizontal_time = len(temp) + rdistance # Number of turns till they can hit you by getting into position and firing
           
        else:
            # Opponent further left
            ldistance, ldest = self.farthest_sight(position, 2)
            left_placement = position[0]-ldistance
            if left_placement < 0:
                left_placement += self.maxx
                
            if left_placement < pose[0] or ldistance==-1:
                ldest = (pose[0], position[1], 3) # Seeking to be in your y but the their x, facing right. Adding orientation to ldest
            else:
                ldest = (ldest[0], ldest[1], 3)
            if ldistance == -1:
                ldistance = pose[0] - position[0]
                if ldistance<0:
                    ldistance += self.maxx
                    
            horizontal_time = len(self.minimum_path(pose, ldest, gameboard)) + ldistance
            
        if pose[1]>position[1]:
            # Opponent is further down
            ddistance, ddest = self.farthest_sight(position, 1)
            
            down_placement = position[1]+ddistance 
            
            if down_placement >= self.maxy:
                down_placement -= self.maxy
            
            if down_placement > pose[1] or ddistance ==-1:
                ddest = (position[0], pose[1], 0) # Seeking to be in your x but the their y, facing up. Also adding orientation
            else:
                ddest = (ddest[0], ddest[1], 0)
            if ddistance == -1:
                ddistance = position[1] - pose[1]
                if ddistance < 0:
                    ddistance += self.maxy
            temp = self.minimum_path(pose, ddest, gameboard)
            vertical_time = len(temp) + ddistance # Number of turns till they can hit you by getting into position and firing
        else:
            # Opponent is further up
            udistance, udest = farthest_sight(position, 0)
            
            up_placement = position[1]+udistance 
            
            if up_placement < 0:
                up_placement += self.maxy
            
            if up_placement < pose[1] or udistance ==-1:
                udest = (position[0], pose[1], 1) # Seeking to be in your x but the their y, facing up. Also adding orientation
            else:
                udest = (udest[0], udest[1], 1)
            if udistance == -1:
                udistance = pose[1] - position[1]
                if udistance < 0:
                    udistance += self.maxy
                    
            # Number of turns till they can hit you by getting into position and firing
            temp = self.minimum_path(pose, udest, gameboard)
            vertical_time = len(temp) + udistance 
        return min(horizontal_time, vertical_time)

        
    def minimum_path(self, pose_a, pose_b, gameboard):
        '''
        minimum number of turns it takes to get from pose A, to pose B
        pose: (position.x,position.y,direction)
        if direction=-1, direction doesn't matter (case of laser)
        treat laser as a wall when it's firing
        
        in dynamic array, a value of 7 is a laser from a turret
        '''

        dynamic_array = [row[:] for row in self.static_array]
        
        openlist = []
        closedlist = []

        x = pose_a[0]
        y = pose_a[1]
        direction = pose_a[2]

        sequence = []
        temp_sequence = self.min_path_helper(pose_a, pose_b, openlist, closedlist, dynamic_array, sequence, 0, gameboard)
        
        sequence.append((x,y, direction))
        
        list_length = len(temp_sequence)
        for i in range(list_length - 2):
            #re-order the list (right now, it is backwards, and does not account for rotation)
            sequence.append(temp_sequence[list_length - i - 1])
            if sequence[-1][2] != sequence[-2][2]:
                sequence[-1] = (temp_sequence[i][0], temp_sequence[i][1], sequence[-2][2])
                sequence.append(temp_sequence[list_length - i - 1])
        return sequence
    

    def min_path_helper(self, pose_a, pose_b, openlist, closedlist, dynamic_array, sequence, turns_ahead, gameboard):
        player = self.player
        if (pose_a[0] == pose_b[0]) and (pose_a[1] == pose_b[1]):
            return sequence
        elif turns_ahead >=8:
            return [pose_a]

        # If the orientation is null (don't care, assign it -1 to avoid errors)
        if pose_a[2] is None:
            pose_a[2] = -1

        # Get surrounding boxes    
        add_to_list = [(pose_a[0], pose_a[1], pose_a[2])]
        if pose_a[0] == 0:
            add_to_list.append((pose_a[0] + 1, pose_a[1], 3))
            add_to_list.append((len(dynamic_array) - 1, pose_a[1], 2))
        elif pose_a[0] == len(dynamic_array) - 1:
            add_to_list.append((pose_a[0] - 1, pose_a[1], 2))
            add_to_list.append((0, pose_a[1], 3))
        else:
            add_to_list.append((pose_a[0] + 1, pose_a[1], 3))
            add_to_list.append((pose_a[0] - 1, pose_a[1], 2))

        if pose_a[1] == 0:
            add_to_list.append((pose_a[0], pose_a[1] + 1, 1))
            add_to_list.append((pose_a[0], len(dynamic_array[0]) - 1, 0))
        elif pose_a[1] == len(dynamic_array) - 1:
            add_to_list.append((pose_a[0], pose_a[1] - 1, 0))
            add_to_list.append((pose_a[0], 0, 1))
        else:
            add_to_list.append((pose_a[0], pose_a[1] + 1, 1))
            add_to_list.append((pose_a[0], pose_a[1] - 1, 0))

        for j in gameboard.turrets:
            if self.turns_until_a_turret_hits_you(j.x, j.y, gameboard, turns_ahead) == 0:
                for count in range(4):
                    dynamic_array[j.x + count + 1][j.y] = 7
                    dynamic_array[j.x - count - 1][j.y] = 7
                    dynamic_array[j.x][j.y + count + 1] = 7
                    dynamic_array[j.x][j.y - count - 1] = 7
                    
        for j in gameboard.bullets:
            bullet_time = self.turns_until_a_bullet_hits_you((player.x, player.y), (j.x, j.y), gameboard)
            if bullet_time > 0 and (bullet_time + gameboard.current_turn) == turns_ahead:
                for count in range(4):
                    dynamic_array[j.x + count + 1][j.y] = 8
                    dynamic_array[j.x - count - 1][j.y] = 8
                    dynamic_array[j.x][j.y + count + 1] = 8
                    dynamic_array[j.x][j.y - count - 1] = 8
                

        for i in add_to_list:
            heuristic = min(abs(i[0] - pose_b[0]) + abs(i[1] - pose_b[1]), abs(gameboard.width- pose_b[0] + i[0]) + abs(gameboard.height- pose_b[1] + i[1]))
            if (dynamic_array[i[0]][i[1]] not in self.blockers) and (dynamic_array[i[0]][i[1]] not in closedlist) and (dynamic_array[i[0]][i[1]] not in openlist):
                openlist.append((i[0], i[1], i[2], heuristic))
            else:
                if dynamic_array[i[0]][i[1]] in self.blockers:
                    if dynamic_array[i[0]][i[1]] not in closedlist:
                        closedlist.append(i)
                    if dynamic_array[i[0]][i[1]] in openlist:
                        openlist.remove(i)
                closedlist.append((i[0], i[1], i[2], heuristic))
        
        min_j = 0
        min_heur = 99
        for j in openlist:
            if j[3] < min_heur:
                min_j = j
                min_heur = j[3]

        openlist.remove(min_j)
        closedlist.append(min_j)
        self.min_path_helper((min_j[0], min_j[1], min_j[2]), pose_b, openlist, closedlist, dynamic_array, sequence, turns_ahead + 1, gameboard)
        sequence.append(((min_j[0], min_j[1], min_j[2])))

        return sequence
    

    def sequence_interpreter(self, sequence):
            '''Return values for :
            Move.FACE_UP
            Move.FACE_DOWN
            Move.FACE_LEFT
            Move.FACE_RIGHT
            Move.NONE
            Move.SHOOT
            Move.FORWARD
            Move.SHIELD
            Move.LASER
            Move.TELEPORT_0
            Move.TELEPORT_1
            Move.TELEPORT_2
            Move.TELEPORT_3
            Move.TELEPORT_4
            Move.TELEPORT_5'''

            #Rotate
            if (sequence[0][0] == sequence[1][0]) and (sequence[0][2] == sequence[1][2]):
                return Move.FORWARD
            
            if (sequence[0][1] == sequence[1][1]) and (sequence[0][2] == sequence[1][2]):
                return Move.FORWARD
            
            if (sequence[0][0] == sequence[1][0]) and (sequence[0][1] == sequence[1][1]):
                if sequence[1][2] == 0:
                    return Move.FACE_UP
                if sequence[1][2] == 1:
                    return Move.FACE_DOWN
                if sequence[1][2] == 2:
                    return Move.FACE_LEFT
                if sequence[1][2] == 3:
                    return Move.FACE_RIGHT

            else:
                return Move.SHOOT

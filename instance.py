import xml.etree.ElementTree as ET
import numpy as np
import copy
import time

# Local packages
import functions as fn


"""
Class for the main instance, stores everything required to define the instance.
"""

class Problem():
    def __init__(self,
                 filename="NA",
                 dummyRoomPenaltyScaling=1,
                 dummyRoomDistanceScaling=1,
                 addDummy=True):
        # User parameters
        self.dummyRoomPenaltyScaling = dummyRoomPenaltyScaling
        self.dummyRoomDistanceScaling = dummyRoomDistanceScaling
        self.addDummy = addDummy
        # Features
        self.filename = filename
        self.problem = ET.parse('data/'+self.filename+'.xml').getroot()
        self.instance_name = self.problem.attrib['name']
        self.number_of_weeks = int(self.problem.attrib['nrWeeks'])
        self.number_of_days = int(self.problem.attrib['nrDays'])
        self.slots_per_day = int(self.problem.attrib['slotsPerDay'])
        # People
        self.students = []
        self.instructors = []
        # Resources
        self.timesets = []
        self.rooms = []
        self.weightedRoomAdjacency = None
        self.roomtimeCompatibility = None # Also known as D0 in papers
        self.timesetoverlaps = []
        # University features
        self.classes = []
        self.modules = []
        # Constraints for layout
        self.distributions = []
        self.distribution_types = []
        self.distribution_arrays = {}
        

    """
    Setting things
    """

    # Function that sets all of the problem elements
    def setAll(self):
        print("Importing timesets")
        self.setTimesets()
        print("Calculating overlapping timesets")
        self.timesetOverlapFinder()
        print("Importing rooms")
        self.setRooms()
        print("Calculating room/time compatibility")
        self.setRTCompatibility()
        print("Importing classes")
        self.setClasses()
        print("Importing module structure")
        self.setModules()
        print("Importing students")
        self.setStudents()
        print("Importing distributions")
        self.setDistributions()
        print("Creating distribution arrays")
        self.setDistributionArrays()


    # Function that collects all of the "timesets" from the classes and then filtering out repeated ones
    def setTimesets(self):
        """
        Function that retrieves timesets from each of the classes,
        then the function removes the repeated timesets,
        then it indexes the times from 0 to n.
        """
        # Collecting all of the timesets from classes
        list_of_timesets = []
        for module in self.problem[2]:
            for module_config in module:
                for module_subpart in module_config:
                    for cls in module_subpart:
                        for resource in cls:
                            if(resource.tag == "time"):
                                new_timeset = Timeset()
                                new_timeset.setAll(resource,self.slots_per_day)
                                list_of_timesets.append(new_timeset)
        # Removing the repeated timesets
        starting_length = len(list_of_timesets)
        new_list_of_timesets = []
        for i in range(starting_length):
            if(i < len(list_of_timesets)):
                comparison_timeset = list_of_timesets[i]
                repeated_indices = []
                for j,tset in enumerate(list_of_timesets[i+1:]):
                    check = fn.timesetIdenticalCheck(tset,comparison_timeset)
                    if(check == True):
                        repeated_indices.append(int(i+j+1))
                list_of_timesets = [x for i, x in enumerate(list_of_timesets) if i not in repeated_indices]
                new_list_of_timesets.append(comparison_timeset)
            else:
                break
        # Index the timesets
        for i,tset in enumerate(new_list_of_timesets):
            tset.id = int(i)
            self.timesets.append(tset)

    
    # Function that runs over all the timesets and finds the ones that overlap
    def timesetOverlapFinder(self):
        """
        Iterations over every timeslot and timeset.
        For a given timeslot a list of timeset id's are stored if that timeset contains that timeslot.
        For some timeslots the list will be empty, these are removed.
        Some timeslots will have identical lists, these repeats are removed.
        """
        timeslot_count = self.number_of_days*self.number_of_weeks*self.slots_per_day
        for tslot in range(timeslot_count):
            # Create list of overlapping timesets
            overlap_list = []
            for tset in self.timesets:
                if(tslot in tset.timeslots):
                    overlap_list.append(tset.id)
            # Check if this list is empty
            if(len(overlap_list) == 0):
                continue
            # Add list if first non-empty addition
            if(len(self.timesetoverlaps) == 0):
                self.timesetoverlaps.append(overlap_list)
                continue
            # Check for repeats
            repeated_list = False
            for previous_overlaps in self.timesetoverlaps:
                if(previous_overlaps == overlap_list):
                    repeated_list = True
                    break
            # Add if not a repeated list
            if(repeated_list == False):
                self.timesetoverlaps.append(overlap_list)
    

    # Function that retrieves all of the rooms and produce array of distances
    def setRooms(self):
        """
        This function first finds all of the rooms and records them as resources.
        Then the function finds the adjacency array with the distances.
        """
        # Adding the dummy room
        dummy_room = Room(roomID=int(0),capacity=int(99999999))
        self.rooms.append(dummy_room)
        # Adding all of the other rooms
        for room in self.problem[1]:
            new_room = Room(roomID=int(room.attrib['id']),capacity=int(room.attrib['capacity']))
            for feature in room:
                if(feature.tag == "unavailable"):
                    new_room.addUnavailable(feature,self.slots_per_day)
            self.rooms.append(new_room)
        # Creating the adjacency matrix
        self.weightedRoomAdjacency = AdjacencyArray(size=len(self.rooms))
        self.weightedRoomAdjacency.setAll(raw_rooms=self.problem[1], dummy_scaling=self.dummyRoomDistanceScaling)

    
    # Function for retrieving classes and information relating to those classes
    def setClasses(self):
        """
        Function takes all of the classes and stores them in the problem.
        Timesets and rooms that they can use are stored as ID's only.
        """
        for module in self.problem[2]:
            for module_config in module:
                for module_subpart in module_config:
                    for cls in module_subpart:
                        # Building the base class object
                        new_class = Class(cls_id=int(cls.attrib['id']),
                                          module=int(module.attrib['id']),
                                          config=int(module_config.attrib['id']),
                                          subpart=int(module_subpart.attrib['id']))
                        # Checking if there is a class limit
                        try:
                            new_class.sub_limit = int(cls.attrib['limit'])
                        except:
                            pass
                        # Checking if there is a parent
                        try:
                            new_class.parent = int(cls.attrib['parent'])
                        except:
                            pass
                        # Adding the rooms
                        try:
                            if(cls.attrib['room'] == "false"):
                                new_class.addRoom(0,float(0))
                        except:
                            maximum_room_penalty = 0
                            for resource in cls:
                                if(resource.tag == "room"):
                                    new_class.addRoom(int(resource.attrib['id']),float(resource.attrib['penalty']))
                                    if(int(resource.attrib['penalty']) > maximum_room_penalty):
                                        maximum_room_penalty = int(resource.attrib['penalty'])
                            if(self.addDummy == True):
                                new_class.addRoom(0,float(maximum_room_penalty*self.dummyRoomPenaltyScaling))
                        # Adding the times
                        for resource in cls:
                            if(resource.tag == "time"):
                                tset_id = 0
                                comparison_timeset = Timeset()
                                comparison_timeset.setAll(resource,self.slots_per_day)
                                for tset in self.timesets:
                                    check = fn.timesetIdenticalCheck(comparison_timeset,tset)
                                    if(check == True):
                                        tset_id = tset.id
                                        break
                                new_class.addTimeset(tset_id,float(resource.attrib['penalty']))
                        # Appending the class object to class list
                        self.classes.append(new_class)


    # Function for setting the structure of modules
    def setModules(self):
        """
        Function takes the structure of modules stores them in the problem.
        Classes are stored as ids only.
        """
        for module in self.problem[2]:
            new_module = Module(module_id=int(module.attrib['id']))
            for module_config in module:
                new_module_config = Config(config_id=int(module_config.attrib['id']))
                for module_subpart in module_config:
                    new_module_subpart = Subpart(subpart_id=int(module_subpart.attrib['id']))
                    for cls in module_subpart:
                        new_module_subpart.classes.append(int(cls.attrib['id']))
                    new_module_config.subparts.append(new_module_subpart)
                new_module.configs.append(new_module_config)
            self.modules.append(new_module)

    # Set all student classes
    def setStudents(self):
        """
        Collects all of the students in an instance,
        records what modules they want to attend.
        Default mode preference is in-person.
        """
        for student in self.problem[4]:
            new_student = Student(studentID=int(student.attrib['id']))
            for module in student:
                new_student.addModule(int(module.attrib['id']))
            self.students.append(new_student)

    
    # Set distributions
    def setDistributions(self):
        """
        This function identifies the type of distribution,
        if there are extra parameters needed,
        if it is required or has a penalty,
        and what classes it impacts.
        """
        for distribution in self.problem[3]:
            # Checking the type of distibution
            dist_type = distribution.attrib['type']
            digit_check = any(char.isdigit() for char in dist_type)
            if(digit_check == False):
                new_distribution = Distribution(distributionType=dist_type)
                self.distribution_types.append(dist_type)
            else:
                dist_type_split = fn.split(dist_type)
                open_bracket = dist_type_split.index('(')
                new_distribution = Distribution(distributionType=dist_type[:open_bracket])
                self.distribution_types.append(dist_type[:open_bracket])
                # Initialising parameters
                parameter_a = ''
                param_a_found = False
                parameter_b = ''
                param_b_found = False
                # Picking out parameters
                for i in range(open_bracket+1,len(dist_type)):
                    char = dist_type_split[i]
                    if(char.isdigit() == True and param_a_found == False):
                        parameter_a += dist_type_split[i]
                    elif(char == ')'):
                        if(param_a_found == True):
                            param_b_found = True
                        else:
                            param_a_found = True
                        break
                    elif(char == ','):
                        param_a_found = True
                    elif(char.isdigit() == True and param_b_found == False):
                        parameter_b += dist_type_split[i]
                    else:
                        print("Unexpected result")
                # Saving extra parameters
                if(param_a_found == True):
                    new_distribution.extra_parameter_A = int(parameter_a)
                if(param_b_found == True):
                    new_distribution.extra_parameter_B = int(parameter_b)
            # Checking if it is required or has a penalty
            try:
                if(distribution.attrib['required'] == "true"):
                    new_distribution.required = True
            except:
                new_distribution.required = False
                new_distribution.penalty = float(distribution.attrib['penalty'])
            # Seeing what classes it impacts
            for cls in distribution:
                new_distribution.addClassID(int(cls.attrib['id']))
            # Saving the distribution
            self.distributions.append(new_distribution)
            self.distribution_types = list(set(self.distribution_types))


    # Produces the compatibility array with corrected indices
    def setRTCompatibility(self):
        self.roomtimeCompatibility = CompatibilityArray(rooms=self.rooms,timesets=self.timesets)


    # Create relevant helper arrays where appropriate
    def setDistributionArrays(self):
        for i,dist_type in enumerate(self.distribution_types):
            print("Creating {} out of {} helper arrays ({})".format(i+1,len(self.distribution_types),dist_type))
            if(dist_type == 'SameStart'):
                array = fn.helperArrayCreation(self.timesets,fn.samestartCheck,entry_type=bool)
                self.distribution_arrays[dist_type] = array
            elif(dist_type == 'SameTime'):
                array = fn.helperArrayCreation(self.timesets,fn.sametimeCheck,entry_type=bool)
                self.distribution_arrays[dist_type] = array
            elif(dist_type == 'DifferentTime'):
                array = fn.helperArrayCreation(self.timesets,fn.differenttimeCheck,entry_type=bool)
                self.distribution_arrays[dist_type] = array
            elif(dist_type == 'SameDays'):
                array = fn.helperArrayCreation(self.timesets,fn.samedayCheck,entry_type=bool)
                self.distribution_arrays[dist_type] = array
            elif(dist_type == 'DifferentDays'):
                array = fn.helperArrayCreation(self.timesets,fn.differentdayCheck,entry_type=bool)
                self.distribution_arrays[dist_type] = array
            elif(dist_type == 'SameWeeks'):
                array = fn.helperArrayCreation(self.timesets,fn.sameweekCheck,entry_type=bool)
                self.distribution_arrays[dist_type] = array
            elif(dist_type == 'DifferentWeeks'):
                array = fn.helperArrayCreation(self.timesets,fn.differentweekCheck,entry_type=bool)
                self.distribution_arrays[dist_type] = array
            elif(dist_type == 'Overlap'):
                array = fn.helperArrayCreation(self.timesets,fn.timesetOverlapCheck,entry_type=bool)
                self.distribution_arrays[dist_type] = array
            elif(dist_type == 'NotOverlap'):
                array = fn.helperArrayCreation(self.timesets,fn.timesetNotOverlapCheck,entry_type=bool)
                self.distribution_arrays[dist_type] = array
            elif(dist_type == 'Precedence'):
                array = fn.helperArrayCreation(self.timesets,fn.precedenceCheck,entry_type=bool)
                self.distribution_arrays[dist_type] = array
            elif(dist_type == 'SameAttendees' or dist_type == 'MinGap'):
                array = fn.helperArrayCreation(self.timesets,fn.distanceCheckInterior,
                                               entry_type=int,slots_per_day=self.slots_per_day)
                self.distribution_arrays["InteriorDistance"] = array
            elif(dist_type == 'WorkDay'):
                array = fn.helperArrayCreation(self.timesets,fn.distanceCheckExterior,
                                               entry_type=int,slots_per_day=self.slots_per_day)
                self.distribution_arrays["ExteriorDistance"] = array


    """
    Modifying the instance after creation
    """

    # Removes students and redundant modules/classes after these are removed
    def remove_students(self,count=None,start=1):
        # Checking parameters
        if(count == None):
            print("No students being removed from instance")
            return
        count = int(count)
        index_start = int(max(int(start - 1),0))
        if(index_start + count >= len(self.students)):
            print("Invalid parameters for removing students")
            return
        print("Removing students apart from {} to {}".format(start,start+count-1))
        # Removing the students
        remaining_students = self.students[index_start:index_start+count]
        self.students = remaining_students
        # Module cleanup
        keep_modules = []
        for student in self.students:
            keep_modules = keep_modules + student.modules
        keep_modules = list(set(keep_modules))
        new_module_list = []
        for module in self.modules:
            if(module.id in keep_modules):
                new_module_list.append(module)
        self.modules = new_module_list
        # Class cleanup
        keep_classes = []
        for module in self.modules:
            for config in module.configs:
                for subpart in config.subparts:
                    keep_classes = keep_classes + subpart.classes
        keep_classes = list(set(keep_classes))
        new_class_list = []
        for cls in self.classes:
            if(cls.id in keep_classes):
                new_class_list.append(cls)
        self.classes = new_class_list
        # Checking distributions
        for dist in self.distributions:
            new_dist_list = []
            for class_id in dist.classes:
                if(class_id in keep_classes):
                    new_dist_list.append(class_id)
            dist.classes = new_dist_list

    
    # Reduce the capacity of the physical spaces by a certain percentage
    def reduce_capacity(self,percentage_decrease):
        percent = max(100-percentage_decrease,0)
        print("Physical room capacity at {}%".format(percent))
        decimal = percent/100
        for room in self.rooms:
            if(room.id != 0):
                room.capacity = int(room.capacity*decimal)

    
    # Assigns the student mode preferences
    def student_preferences(self,proportion=(1,1,1)):
        print("Modifying student preferences with the proportion {}".format(proportion))
        total_students_considered = 0
        while True:
            # First
            for i in range(proportion[0]):
                self.students[total_students_considered].mode_preference = 1
                total_students_considered += 1
            if(total_students_considered == len(self.students)):
                break
            # Second
            for i in range(proportion[1]):
                self.students[total_students_considered].mode_preference = 0
                total_students_considered += 1
            if(total_students_considered == len(self.students)):
                break
            # Third
            for i in range(proportion[2]):
                self.students[total_students_considered].mode_preference = -1
                total_students_considered += 1
            if(total_students_considered == len(self.students)):
                break


"""
Advanced adjacency array
"""

class AdjacencyArray():
    """
    This is needed because some of the room indices are skipped.
    This means rooms IDs don't correspond perfectly with array indices.
    """
    def __init__(self,size=1):
        self.array = np.zeros((size,size))
        self.id_dictionary = {0:0}

    def setAll(self,raw_rooms,dummy_scaling):
        # Creating dictionary to map room id's to indices
        for i,room in enumerate(raw_rooms):
            self.id_dictionary[int(room.attrib['id'])] = i+1
        # Populating array
        for room in raw_rooms:
            for feature in room:
                if(feature.tag == "travel"):
                    rid1 = int(room.attrib['id'])
                    rid2 = int(feature.attrib['room'])
                    rindex1 = self.id_dictionary[rid1]
                    rindex2 = self.id_dictionary[rid2]
                    self.array[rindex1,rindex2] = float(feature.attrib['value'])
                    self.array[rindex2,rindex1] = float(feature.attrib['value'])
        # Distance for dummy room
        max_distance = self.array.max()
        for i in range(self.array.shape[0]):
            if(i != 0):
                self.array[0,i] = float(max_distance*dummy_scaling)
                self.array[i,0] = float(max_distance*dummy_scaling)
    
    def distance(self,room_id1,room_id2):
        rindex1 = self.id_dictionary[room_id1]
        rindex2 = self.id_dictionary[room_id2]
        return self.array[rindex1,rindex2]
    
"""
Room time compatibility array
"""

class CompatibilityArray():
    """
    This is needed because some of the room indices are skipped.
    This means rooms IDs don't correspond perfectly with array indices.
    """
    def __init__(self,rooms,timesets):
        self.id_dictionary = {}
        self.setAll(rooms,timesets)

    def setAll(self,rooms,timesets):
        self.array = np.zeros((len(rooms),len(timesets)),dtype=bool)
        # Creating dictionary to map room id's to indices
        for i,room in enumerate(rooms):
            self.id_dictionary[room.id] = i
        # Populating array
        for room in rooms:
            for timeset in timesets:
                #print("Checking if room {} is compatible with {}".format(room.id,timeset.id))
                comp_check = fn.roomtimeCompatibleCheck(room,timeset)
                self.array[self.id_dictionary[room.id],timeset.id] = comp_check
    
    def compatible(self,room_id,timeset_id):
        return self.array[self.id_dictionary[room_id],timeset_id]

"""
Class for timeset object
"""

class Timeset():
    def __init__(self,timesetID=int(0)):
        self.id = timesetID
        self.timeslots = []
        self.days = []
        self.weeks = []
        self.length = 0
        self.start = 0
        self.classes = []
    
    def addClass(self,classID):
        self.classes.append(classID)
    
    def setAll(self,RawTimeset,slotsPerDay):
        # Setting length and start
        self.length = int(RawTimeset.attrib['length'])
        self.start = int(RawTimeset.attrib['start'])
        # Splitting the days and week string
        weeks = fn.split(RawTimeset.attrib['weeks'])
        days = fn.split(RawTimeset.attrib['days'])
        for w in range(len(weeks)):
            # Calculating which weeks timeset has
            if(weeks[w] == '1'):
                self.weeks.append(int(w+1))
            for d in range(len(days)):
                # Calculating which days timeset has
                if(days[d] == '1'):
                    self.days.append(int(d+1))
                    # Calculating the slots that are in the timeset
                    if(weeks[w] == '1'):
                        slot = w*len(days)*slotsPerDay + d*slotsPerDay + self.start
                        for l in range(self.length):
                            self.timeslots.append(int(slot+l))
        # Will have over-appended days so removing repeats
        self.days = list(set(self.days))
        # Sorting all of the lists
        self.timeslots.sort()
        self.days.sort()
        self.weeks.sort()
        self.classes.sort()
    

"""
Class for a room object
"""

class Room():
    def __init__(self,roomID=int(0),capacity=int(0)):
        self.id = roomID
        self.unavailable = []
        self.capacity = capacity
        self.hybridcapable = False
        if(self.capacity >= 30):
            self.hybridcapable = True

    def addUnavailable(self,RawTimeset,slotsPerDay):
        unavailable_slots = []
        # Setting length and start
        length = int(RawTimeset.attrib['length'])
        start = int(RawTimeset.attrib['start'])
        # Splitting the days and week string
        weeks = fn.split(RawTimeset.attrib['weeks'])
        days = fn.split(RawTimeset.attrib['days'])
        for w in range(len(weeks)):
            for d in range(len(days)):
                if(days[d] == '1' and weeks[w] == '1'):
                    slot = w*len(days)*slotsPerDay + d*slotsPerDay + start
                    for l in range(length):
                        unavailable_slots.append(int(slot+l))
        # Adding the unavailable slots
        self.unavailable = list(set(self.unavailable + unavailable_slots))


"""
Class for taught class object
"""

class Class():
    def __init__(self,cls_id=int(0),module=int(0),config=int(0),subpart=int(0)):
        self.id = cls_id
        self.module = module
        self.module_config = config
        self.module_subpart = subpart
        self.rooms = {}
        self.timesets = {}
        self.parent = None
        self.sub_limit = int(999999)
        
    def addRoom(self,room,penalty):
        self.rooms[room] = penalty
            
    def addTimeset(self,timeset,penalty):
        self.timesets[timeset] = penalty
            
"""
Class for a distribution object.
"""    

class Distribution():
    def __init__(self,distributionType="NA"):
        self.type = distributionType
        self.required = False
        self.penalty = 0
        self.classes = []
        self.extra_parameter_A = None 
        self.extra_parameter_B = None 
        
    def addClassID(self,classID):
        self.classes.append(classID)
        

"""
Class for students
"""

class Student():
    def __init__(self,studentID=int(0)):
        self.id = studentID
        self.modules = []
        self.required_modules = []
        self.mode_preference = 1
        
    def addModule(self,module_id,required = False):
        self.modules.append(module_id)
        if(required == True):
            self.required_modules.append(module_id)


"""
Classes to store information about a course
"""

# Overarching course structure, will contain other auxilliary structures
class Module():
    def __init__(self,module_id=int(0)):
        self.id = module_id
        self.configs = []

# Config structure
class Config():
    def __init__(self,config_id=int(0)):
        self.id = config_id
        self.subparts = []
    
# Subpart structure
class Subpart():
    def __init__(self,subpart_id=int(0)):
        self.id = subpart_id
        self.classes = []


"""
Fixed elements object
"""

class FixedElements:
    def __init__(self,P):
        self.students = []
        self.classes = []
        self.P = P

    # Fixing students
    # Fix students -> fix a selection of classes
    def fix_students(solution,student_ids):
        pass
    # Fixing classes
    # Fix classes -> maybe end up fixing students
    def fix_classes(solution,class_ids):
        pass
            
            
        
         
    
    

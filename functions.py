"""
This file contains many of the functions used to perform tasks outside of optimisation.
"""
import numpy as np
import pickle
import itertools

# Local packages
import instance as inst

"""
ACTUALLY USED FUNCTIONS
"""

# Splits a string into individual elements of a string
def split(word):
    return [char for char in word]

# Function takes two lists and returns the intersection of the two lists
def intersection(lst1, lst2):
    lst3 = [value for value in lst1 if value in lst2]
    return lst3

# Check if two timesets are exactly the same
def timesetIdenticalCheck(T1,T2):
    week_intersect = intersection(T1.weeks,T2.weeks)
    if(week_intersect == T1.weeks and week_intersect == T2.weeks):
        day_intersect = intersection(T1.days,T2.days)
        if(day_intersect == T1.days and day_intersect == T2.days):
            if(T1.start == T2.start):
                if(T1.length == T2.length):
                    return True
    return False

# Reports the number of key features
def feature_check(P):
    print("Number of students: "+str(len(P.students)))
    print("Number of modules: "+str(len(P.modules)))
    print("Number of classes: "+str(len(P.classes)))
    print("Number of timesets: "+str(len(P.timesets)))
    print("Number of rooms: "+str(len(P.rooms)))

# Count number of hybrid capable rooms
def hybrid_capable_count(P):
    count = 0
    for r in P.rooms:
        if(r.id != 0):
            if(r.hybridcapable == True):
                count += 1
    return count

"""
Instance import function
"""

# Checks if a problem instance exists and if not make it and save it
def instanceImport(filename="NA",
                   dummyRoomPenaltyScaling=1,
                   dummyRoomDistanceScaling=1,
                   addDummy=True,
                   force_reset=False):
    if(force_reset == False):
        try:
            infile = open("processed_data/"+filename+"_instance","rb")
            print("Converted problem instance found!")
            print("Importing instance: " + filename)
            P = pickle.load(infile)
            infile.close()
        except:
            print("Warning: Converted problem instance NOT found!")
            print("Creating instance: " + filename)
            P = inst.Problem(filename=filename,
                             dummyRoomPenaltyScaling=dummyRoomPenaltyScaling,
                             dummyRoomDistanceScaling=dummyRoomDistanceScaling,
                             addDummy=addDummy)
            P.setAll()
            outfile = open("processed_data/"+filename+"_instance","wb")
            pickle.dump(P, outfile)
            outfile.close()
    else:
        print("Warning: Forcing reset of instance")
        print("Importing and formatting instance: " + filename)
        P = inst.Problem(filename=filename,
                         dummyRoomPenaltyScaling=dummyRoomPenaltyScaling,
                         dummyRoomDistanceScaling=dummyRoomDistanceScaling,
                         addDummy=addDummy)
        P.setAll()
        outfile = open("processed_data/"+filename+"_instance","wb")
        pickle.dump(P, outfile)
        outfile.close()
    return P

"""
Resource relation functions
"""

# Checks if a timeset overlaps with a rooms unavailable times
def roomtimeCompatibleCheck(R,T):
    """
    Returns "False" if room is not compatible with timeset
    """
    if(intersection(R.unavailable,T.timeslots)):
        return False
    return True

# Checks if two timesets overlap at all
def timesetOverlapCheck(T1,T2):
    """
    Checks if two timesets overlap at all
    ITC2019: "Overlap"
    """
    # if(intersection(T1.timeslots,T2.timeslots)):
    #     return True
    # return False

    # Check if they share weeks
    if(len(intersection(T1.weeks,T2.weeks)) == 0):
        return False
    # Check if they share days
    if(len(intersection(T1.days,T2.days)) == 0):
        return False
    # Check if they overlap
    slots1 = [int(T1.start+i) for i in range(T1.length)]
    slots2 = [int(T2.start+i) for i in range(T2.length)]
    if(len(intersection(slots1,slots2)) == 0):
        return False
    return True
    

# Checks if two timesets don't overlap
def timesetNotOverlapCheck(T1,T2):
    """
    Checks if two timesets do not overlap at all
    ITC2019: "NotOverlap"
    """
    if(timesetOverlapCheck(T1,T2)):
        return False
    return True

# Checks if two times have the same start
def samestartCheck(T1,T2):
    """
    Checks if two timesets have the same start time
    ITC2019: "SameStart"
    """
    if(T1.start == T2.start):
        return True
    return False
    
# Checks if two times occur within the same timeframe (ignoring days and weeks) 
def sametimeCheck(T1,T2):
    """
    Checks if two timesets occur at the same time (overlap ignoring days and weeks)
    ITC2019: "SameTime"
    """
    start1 = T1.start
    end1 = start1 + T1.length
    start2 = T2.start
    end2 = start2 + T2.length
    if((start1 <= start2 and end2 <= end1) or (start2 <= start1 and end1 <= end2)):
        return True
    return False
    
# Checks if two times do not occur within the same timeframe (ignoring days and weeks) 
def differenttimeCheck(T1,T2):
    """
    Checks if two timesets do not occur at the same time (overlap ignoring days and weeks)
    ITC2019: "DifferentTime"
    """
    start1 = T1.start
    end1 = start1 + T1.length
    start2 = T2.start
    end2 = start2 + T2.length
    if((end2 <= start1) or (end1 <= start2)):
        return True
    return False
    
# Checks if two times share the same days
def samedayCheck(T1,T2):
    """
    Checks if two timesets occur on the same days
    ITC2019: "SameDays"
    """
    days1 = set(T1.days)
    days2 = set(T2.days)
    daysBoth = days1.intersection(days2)
    if(daysBoth.issubset(days1) and days1.issubset(daysBoth)):
        return True
    elif(daysBoth.issubset(days2) and days2.issubset(daysBoth)):
        return True
    return False
    
# Checks if two times do not share any of the same days
def differentdayCheck(T1,T2):
    """
    Checks if two timesets don't share any days
    ITC2019: "DifferentDays"
    """
    days1 = set(T1.days)
    days2 = set(T2.days)
    daysBoth = days1.intersection(days2)
    if(len(daysBoth) == 0):
        return True
    return False
    
# Checks if two times share the same weeks
def sameweekCheck(T1,T2):
    """
    Checks if two timesets occur on the same weeks
    ITC2019: "SameWeeks"
    """
    weeks1 = set(T1.weeks)
    weeks2 = set(T2.weeks)
    weeksBoth = weeks1.intersection(weeks2)
    if(weeksBoth.issubset(weeks1) and weeks1.issubset(weeksBoth)):
        return True
    elif(weeksBoth.issubset(weeks2) and weeks2.issubset(weeksBoth)):
        return True
    return False
    
# Checks if two times do not share any of the same weeks
def differentweekCheck(T1,T2):
    """
    Checks if two timesets don't share any weeks
    ITC2019: "DifferentWeeks"
    """
    weeks1 = set(T1.weeks)
    weeks2 = set(T2.weeks)
    weeksBoth = weeks1.intersection(weeks2)
    if(len(weeksBoth) == 0):
        return True
    return False
    
# Calculates interior "distance" in slot numbers between two timesets
def distanceCheckInterior(slots_per_day,T1,T2):
    """
    This function returns
    - Number of slots in a day if they don't ever share a same day or week
    - Distance (interior) between the two timesets if they share day and week
    - Zero if the end of one session is the start of another
    - Negative ten if the timesets overlap
    ITC2019: Partial "SameAttendees", "MinGap"
    """
    if(differentweekCheck(T1,T2) == True): # Check if they share weeks
        return int(slots_per_day)
    elif(differentdayCheck(T1,T2) == True): # Check if they share days
        return int(slots_per_day)
    else: # If yes work out distance between them
        start1 = T1.start
        end1 = start1 + T1.length
        start2 = T2.start
        end2 = start2 + T2.length
        if(start1 < start2 and end1 < start2):
            return int(start2 - end1)
        elif(start2 < start1 and end2 < start1):
            return int(start1 - end2)
        elif(end1 == start2 or end2 == start1):
            return int(0)
        else:
            return int(-10)
        
# Calculates "exterior distance" in slot numbers between two times
def distanceCheckExterior(slots_per_day,T1,T2):
    """
    This function returns
    - Number of slots in a day if they don't ever share a same day or week
    - Distance (exterior) between the two timesets if they share day and week
    - Length of the timesets if they overlap perfectly
    ITC2019: Partial "WorkDay"
    """
    if(differentweekCheck(T1,T2) == True): # Check if they share weeks
        return int(slots_per_day)
    elif(differentdayCheck(T1,T2) == True): # Check if they share days
        return int(slots_per_day)
    else: # If yes work out distance between them
        start1 = T1.start
        end1 = start1 + T1.length
        start2 = T2.start
        end2 = start2 + T2.length
        return int(max(end1,end2)-min(start1,start2))
    
# Checks if the first meeting of T1 precedes the first meeting of T2
def precedenceCheck(T1,T2):
    """
    Checks if the first meeting of T1 precedes first meeting of T2
    ITC2019: "Precedence"
    """
    # Check if T1 is in an earlier week than T2
    FirstWeek1 = T1.weeks[0]
    FirstWeek2 = T2.weeks[0]
    if(FirstWeek1 < FirstWeek2):
        return True
    elif(FirstWeek1 > FirstWeek2):
        return False
    # Same start week so check if T1 is on an earlier day than T2
    FirstDay1 = T1.days[0]
    FirstDay2 = T2.days[0]
    if(FirstDay1 < FirstDay2):
        return True
    elif(FirstDay1 > FirstDay2):
        return False
    # Same week and day, check if T1 finishes before T2 starts
    Start1 = T1.start
    End1 = Start1 + T1.length
    Start2 = T2.start
    if(End1 <= Start2):
        return True
    else:
        return False

"""
Helper array creation
"""

def helperArrayCreation(timesets,check_function,entry_type=bool,slots_per_day=None):
    array = np.zeros((len(timesets),len(timesets)),dtype=entry_type)
    for T1 in timesets:
        for T2 in timesets:
            if(slots_per_day == None):
                array[T1.id,T2.id] = check_function(T1,T2)
                array[T2.id,T1.id] = check_function(T2,T1)
            else:
                array[T1.id,T2.id] = check_function(slots_per_day,T1,T2)
                array[T2.id,T1.id] = check_function(slots_per_day,T2,T1)
    return array

"""
Function to check if we can skip student scheduling constraints
"""

def skip_student_scheduling_issues(c1,c2):
    """
    Returns true if it is okay to skip student scheduling issue constraints
    Returns false if we need to include those constraints
    DOES NOT mean ignore overlap or sa constraints as these apply for "instructors"
    """
    # Check if classes are in same module
    if(c1.module == c2.module):
        # Check if classes are in the same config of the same module
        if(c1.module_config != c2.module_config):
            return True
        else:
            # Check if they are in the same subpart of the same config
            if(c1.module_subpart == c2.module_subpart):
                return True
            else:
                return False
    else:
        return False

"""
Takes two classes and returns the largest distance between them
"""

def max_travel_distance(P,c1,c2):
    max_distance = 0
    for r1 in c1.rooms:
        for r2 in c2.rooms:
            dist = P.weightedRoomAdjacency.distance(r1,r2)
            if(dist >= max_distance):
                max_distance = dist
    return max_distance

"""
Solution analysis
"""

# Attendance breakdown
def attendance_breakdown(xml_solution):
    """
    Function finds the attendance metrics for an instance.
    """
    attendance_breakdown = {"total": 0,
                            "inperson": 0,
                            "online": 0}
    for cls in xml_solution:
        for student in cls:
            attendance_breakdown["total"] += 1
            if(student.attrib["mode"] == "online"):
                attendance_breakdown["online"] += 1
            else:
                attendance_breakdown["inperson"] += 1
    return attendance_breakdown


# Switch counting
def switch_detection(xml_solution):
    """
    Functions finds the number of students who at some point,
    switch modes more than once in a single day.
    """
    students_who_have_two_switches = []
    # Finding how many weeks there are
    max_weeks = 0
    for cls in xml_solution:
        if(max(cls.attrib["weeks"]) >= max_weeks):
            max_weeks = max(cls.attrib["weeks"])
    all_weeks = [i+1 for i in range(max_weeks)]
    for week in all_weeks:
        for day in [1,2,3,4,5,6,7]:
            # Identify students who take a class on a certain day on a certain week
            student_list = []
            for cls in xml_solution:
                if(day in cls.attrib["days"] and week in cls.attrib["weeks"]):
                    for student in cls:
                        student_list.append(student.attrib["id"])
            student_list = list(set(student_list))
            # Iterate through these students and identify the start time and mode
            for s in student_list:
                activity = []
                for cls in xml_solution:
                    if(day in cls.attrib["days"] and week in cls.attrib["weeks"]):
                        for student in cls:
                            if(student.attrib["id"] == s):
                                activity.append((cls.attrib["start"],student.attrib["mode"]))
                # Sort the activities by starting time and then discard time
                activity = sorted(activity, key=lambda x: x[0])
                activity = [x[1] for x in activity]
                # Count the switches
                switches = 0
                for i in range(len(activity)):
                    if(i != 0):
                        if(activity[i-1] != activity[i]):
                            switches += 1
                # If switches greater than 2 then log student
                if(switches >= 2):
                    students_who_have_two_switches.append(s)
    # Clean up the list of students
    students_who_have_two_switches = list(set(students_who_have_two_switches))
    switch_breakdown = {"total": len(students_who_have_two_switches), 
                        "students": students_who_have_two_switches}
    return switch_breakdown


# Electives offered
def elective_breakdown(P,xml_solution):
    """
    Approximates the number of electives attended by each student
    """
    elective_breakdown = {}
    for s in P.students:
        # Workout what electives exist
        electives = list(set(s.modules)-set(s.required_modules))
        # Check if elective is attended
        attended_electives = []
        for cls in xml_solution:
            for student in cls:
                if(student.attrib["id"] == s.id):
                    for c in P.classes:
                        if(c.id == cls.attrib["id"]):
                            attended_electives.append(c.module)
        # Filter out repeats and recording 100 for no electives
        attended_electives = list(set(attended_electives))
        if(len(electives) == 0):
            elective_breakdown[s.id] = float(100)
            continue
        # Recording electives if some are requested
        elective_breakdown[s.id] = float((len(attended_electives)/len(electives))*100)
    return elective_breakdown


# Conflict breakdown
def conflict_breakdown(P,xml_solution):
    """
    Works out the number of conflicts that each student experiences
    """
    conflict_breakdown = {}
    for s in P.students:
        # Working out what classes are taken by this student, how they attend, and what time
        classes_taken = []
        for cls in xml_solution:
            for student in cls:
                if(student.attrib["id"] == s.id):
                    # Recording the class
                    class_id = cls.attrib["id"]
                    # Recording the room
                    if(student.attrib["mode"] == "online"):
                        room_id = 0
                    else:
                        room_id = cls.attrib["room"]
                    # Recording the timeset
                    for t in P.timesets:
                        if(t.weeks == cls.attrib["weeks"] and
                           t.days == cls.attrib["days"] and
                           t.start == cls.attrib["start"] and
                           t.length == cls.attrib["length"]):
                            timeset_id = t.id
                            break
                    # Recoridng tuple
                    classes_taken.append((class_id,room_id,timeset_id))
        # Checking if a conflicts exist
        D_array_sameattendee = P.distribution_arrays["InteriorDistance"]
        conflict_count = 0
        class_pair_combos = itertools.combinations(classes_taken, 2)
        for pair in class_pair_combos:
            c1 = pair[0]
            c2 = pair[1]
            if(P.weightedRoomAdjacency.distance(c1[1],c2[1]) > D_array_sameattendee[c1[2],c2[2]]):
                conflict_count += 1
        # Recording conflict count
        conflict_breakdown[s.id] = conflict_count
    return conflict_breakdown


# Mode breakdown
def mode_breakdown(P,xml_solution):
    """
    This function takes a problem instance and solution and for each student
    identifies the percentage of classes attended in correct mode.
    """
    mode_breakdown_dictionary = {}
    for s in P.students:
        # Skipping students who don't care, checking those who do
        if(s.mode_preference == 0):
            mode_breakdown_dictionary[s.id] = float(100)
            continue
        elif(s.mode_preference == 1):
            ideal = "inperson"
        else:
            ideal = "online"
        # Checking
        class_count = 0
        correct_mode = 0
        for cls in xml_solution:
            for student in cls:
                if(student.attrib["id"] == s.id):
                    class_count += 1
                    if(student.attrib["mode"] == ideal):
                        correct_mode += 1
        # Recording 100 if none attended
        if(class_count == 0):
            mode_breakdown_dictionary[s.id] = float(100)
            continue
        # Recording percentage if attended
        mode_breakdown_dictionary[s.id] = float((correct_mode/class_count)*100)
    return mode_breakdown_dictionary
from gurobipy import Model, GRB, quicksum, tupledict, LinExpr, Env # Required for optimisation
import gurobipy
import numpy as np
import itertools
import time
import copy
import xml.etree.ElementTree as ET

# Local packages
import functions as fn
from instance import FixedElements

"""
Model object
"""
  
class ModelObject:
    def __init__(self, problem_instance, 
                 solution = None,
                 fixed_elements = None,
                 inactive_constraints = [], 
                 number_cores = None, 
                 node_memory=1.0,
                 console_output = True,
                 feasible_only = False,
                 presolve = -1,
                 mipgap = 0):
        
        # Required variables
        self.P = problem_instance
        
        # Optional input
        self.solution = solution
        self.fixed_elements = fixed_elements
        self.inactive_constraints = inactive_constraints
        
        # Solver specific variables
        self.number_cores = number_cores
        self.node_memory = node_memory
        self.console_output = console_output
        self.feasible_only = feasible_only
        self.presolve = presolve
        self.mipgap = mipgap
        
        # Building the model
        self.inititialise_model()

        # Adding variables
        print("Adding variables to model")
        self.addVariablesBase()
        if(self.fixed_elements != None and self.solution != None):
            self.fixVariablesBase()

        # Adding constraints
        print("Adding constraints to model")
        self.addBaseConstraints()


    """
    Basic setup of model
    """

    # Create the model and decide if it produces any output or not
    def inititialise_model(self):
        """
        This function creates the model and embeds all of the solver options.
        """
        # Creating model with or without output
        if(self.console_output != True):
            env = Env(empty=True)
            env.setParam("OutputFlag",0)
            env.start()
            self.M = Model("University timetabling problem", env = env)
        else:
            self.M = Model("University timetabling problem")
        # Other model variables
        self.M.Params.NodefileStart = self.node_memory
        if(self.feasible_only == True):
            self.M.Params.SolutionLimit = 1
        if(self.number_cores != None):
            self.M.Params.Threads = self.number_cores
        self.M.Params.Presolve = self.presolve
        self.M.Params.MIPGap = self.mipgap
        
    
    """
    Optimise the model
    """
    
    def solve_model(self):
        self.optimise_model()
        self.updateSolution()
    
    def optimise_model(self):
        print("Optimising the model")
        self.M.optimize()
    
    def updateSolution(self):
        print("Creating model solution file")
        # Creating the main file
        sol = ET.Element("solution")
        sol.attrib["name"] = self.P.filename
        # Adding the classes that are being ran
        for c in self.P.classes:
            class_info = {"id": c.id, "room": None, "online": None}
            for r in c.rooms:
                for t in c.timesets:
                    if(self.x[c.id,r,t].X != 0):
                        # Appending the time
                        timeset = self.P.timesets[t]
                        class_info["days"] = timeset.days
                        class_info["start"] = timeset.start
                        class_info["length"] = timeset.length
                        class_info["weeks"] = timeset.weeks
                        # Appending the room
                        if(r == 0):
                            class_info["online"] = True
                        else:
                            class_info["room"] = r
            if(len(class_info) > 3):
                cls_add = ET.SubElement(sol, "class")
                cls_add.attrib = class_info
                # Adding the students who are attending this class
                for var in self.alphaonl:
                    if(self.alphaonl[var].X != 0 and var[1] == c.id):
                        student_add = ET.SubElement(cls_add, "student")
                        student_add.attrib = {"id": var[0], "mode": "online"}
                    if(self.alphainp[var].X != 0 and var[1] == c.id):
                        student_add = ET.SubElement(cls_add, "student")
                        student_add.attrib = {"id": var[0], "mode": "inperson"}
        # Saving solution to the object (replaces any input solution)
        self.solution = sol

    """
    Adding model variables
    """

    def addVariablesBase(self):
        # Add the base model variables
        self.addVarBaseX()
        self.addVarBaseYRandYT()
        self.addVarBaseGQW()
        self.addVarBaseStudent()
        # Update the model
        self.M.update()
    
    # Adding the x variables
    def addVarBaseX(self):
        self.x = tupledict()
        for c in self.P.classes:
            for r in c.rooms:
                for t in c.timesets:
                    self.x[c.id,r,t] = self.M.addVar(vtype=GRB.BINARY)

    # Adding the yr and yt variables
    def addVarBaseYRandYT(self):
        self.yr = tupledict()
        self.yt = tupledict()
        for c in self.P.classes:
            # YR variables
            for r in c.rooms:
                self.yr[c.id,r] = self.M.addVar(vtype=GRB.BINARY)
            # YT variables
            for t in c.timesets:
                self.yt[c.id,t] = self.M.addVar(vtype=GRB.BINARY)

    # Adding the g, q and w variables (course offering variables)
    def addVarBaseGQW(self):
        self.g = tupledict()
        self.q = tupledict()
        self.w = tupledict()
        for k in self.P.modules:
            self.g[k.id] = self.M.addVar(vtype=GRB.BINARY)
            for f in k.configs:
                self.q[k.id,f.id] = self.M.addVar(vtype=GRB.BINARY)
                for p in f.subparts:
                    self.w[k.id,f.id,p.id] = self.M.addVar(vtype=GRB.BINARY)
    
    # Adding the student related variables
    def addVarBaseStudent(self):
        # Initialising all of the variables that are present
        self.a = tupledict()
        self.alphaonl = tupledict()
        self.alphainp = tupledict()
        self.tau = tupledict()
        self.b = tupledict()
        self.m = tupledict()
        self.n = tupledict()
        self.betaonl = tupledict()
        self.betainp = tupledict()
        self.gamma = tupledict()
        self.h = tupledict()
        # Adding variables for each student
        for s in self.P.students:
            classes_for_student = []
            for k in self.P.modules:
                if(k.id in s.modules):
                    self.n[s.id,k.id] = self.M.addVar(vtype=GRB.BINARY)
                    for f in k.configs:
                        self.m[s.id,k.id,f.id] = self.M.addVar(vtype=GRB.BINARY)
                        for p in f.subparts:
                            self.b[s.id,k.id,f.id,p.id] = self.M.addVar(vtype=GRB.BINARY)
                            for c in self.P.classes:
                                if(c.id in p.classes):
                                    self.a[s.id,k.id,f.id,p.id,c.id] = self.M.addVar(vtype=GRB.BINARY)
                                    self.alphaonl[s.id,c.id] = self.M.addVar(vtype=GRB.BINARY)
                                    self.alphainp[s.id,c.id] = self.M.addVar(vtype=GRB.BINARY)
                                    self.tau[s.id,c.id] = self.M.addVar(vtype=GRB.BINARY)
                                    classes_for_student.append(c.id)
                                    for t in c.timesets:
                                        self.betaonl[s.id,c.id,t] = self.M.addVar(vtype=GRB.BINARY)
                                        self.betainp[s.id,c.id,t] = self.M.addVar(vtype=GRB.BINARY)
                                        for r in c.rooms:
                                            self.gamma[s.id,c.id,r,t] = self.M.addVar(vtype=GRB.BINARY)
            class_pair_combos = itertools.combinations(classes_for_student, 2)
            for pair in class_pair_combos:
                if(pair[0] < pair[1]):
                    self.h[s.id,pair[0],pair[1]] = self.M.addVar(vtype=GRB.BINARY)
                else:
                    self.h[s.id,pair[1],pair[0]] = self.M.addVar(vtype=GRB.BINARY)
                    

    """
    Fixing variables according to the provided or current solution
    """

    def fixVariablesBase(self):
        # Retrieving fixed elements
        fixed_classes = self.fixed_elements.classes
        fixed_students = self.fixed_elements.students

        # Fixing the x, yr and yt variables
        for fc in fixed_classes:
            self.fix_class_variables(fc)  
        # Fixing the g, q and w variables (course offering variables)
        # Fixing the student related variables
        for fs in fixed_students:
            self.fix_student_variables(fs)

    # Fixing the class variables
    def fix_class_variables(self,fc):
        """
        Takes a fixed class and fixes the x variables and
        also fixes the yt and yr variables for a class. 
        """
        solution = self.solution
        # Getting the class object
        for c_check in self.P.classes:
            if(c_check.id == fc):
                c = c_check
                break
        # Check if class has an allocation at all
        timeset = None
        room = None
        online = None
        for c_sol in solution:
            if(c_sol.attrib['id'] == fc):
                # Locations
                room = c_sol.attrib['room']
                online = c_sol.attrib['online']
                # Timeset
                days = c_sol.attrib['online']
                start = c_sol.attrib['start']
                length = c_sol.attrib['length']
                weeks = c_sol.attrib['weeks']
                for t in self.P.timesets:
                    if(t.days == days and
                       t.start == start and
                       t.length == length and
                       t.weeks == weeks):
                        timeset = t.id
                break
        # Fixing the x variables
        for r in c.rooms:
            for t in c.timesets:
                if(r == 0 and t == timeset and online == True):
                    self.x[c.id,r,t].ub = 1
                    self.x[c.id,r,t].lb = 1
                elif(r == room and t == timeset):
                    self.x[c.id,r,t].ub = 1
                    self.x[c.id,r,t].lb = 1
                else:
                    self.x[c.id,r,t].ub = 0
                    self.x[c.id,r,t].lb = 0
        # Fixing the yr and yt variables
        for r in c.rooms:
            if(r == 0 and online == True):
                self.yr[c.id,r].ub = 1
                self.yr[c.id,r].lb = 1
            elif(r == room):
                self.yr[c.id,r].ub = 1
                self.yr[c.id,r].lb = 1
            else:
                self.yr[c.id,r].ub = 0
                self.yr[c.id,r].lb = 0
        for t in c.timesets:
            if(t == timeset):
                self.yt[c.id,t].ub = 1
                self.yt[c.id,t].lb = 1
            else:
                self.yt[c.id,t].ub = 0
                self.yt[c.id,t].lb = 0

    # Fixing the student variables
    def fix_student_variables(self,fs):
        """
        Takes a student and ensures that they still attend
        the same classes in the same mode.
        It fixes the variables associated with that student.
        """
        solution = self.solution
        # Getting the student who is fixed
        for s_check in self.P.students:
            if(s_check.id == fs):
                s = s_check
                break
        # Getting all of the classes that student fs is attending (with mode)
        attended_classes = {}
        for c_sol in solution:
            for s_sol in c_sol:
                if(s_sol.attrib['id'] == fs):
                    attended_classes[c_sol.attrib['id']] = s_sol.attrib['mode']
        # Fixing the "a" student variable
        classes_for_student = []
        for k in self.P.modules:
            if(k.id in s.modules):
                for f in k.configs:
                    for p in f.subparts:
                        for c in self.P.classes:
                            if(c.id in p.classes):
                                classes_for_student.append(c.id)
                                if(c.id in list(attended_classes.keys())):
                                    self.a[s.id,k.id,f.id,p.id,c.id].ub = 1
                                    self.a[s.id,k.id,f.id,p.id,c.id].lb = 1
                                else:
                                    self.a[s.id,k.id,f.id,p.id,c.id].ub = 0
                                    self.a[s.id,k.id,f.id,p.id,c.id].lb = 0
        # Fixing the alphas and taus
        for c_id in classes_for_student:
            if(c_id not in list(attended_classes.keys())):
                self.alphaonl[s.id,c_id].ub = 0
                self.alphaonl[s.id,c_id].lb = 0
                self.alphainp[s.id,c_id].ub = 0
                self.alphainp[s.id,c_id].lb = 0
                self.tau[s.id,c_id].ub = 0
                self.tau[s.id,c_id].lb = 0
                for t in c.timesets:
                    self.betaonl[s.id,c_id,t].ub = 0
                    self.betaonl[s.id,c_id,t].lb = 0
                    self.betainp[s.id,c_id,t].ub = 0
                    self.betainp[s.id,c_id,t].lb = 0
                    for r in c.rooms:
                        self.gamma[s.id,c_id,t,r,t].ub = 0
                        self.gamma[s.id,c_id,t,r,t].lb = 0
            elif(attended_classes[c_id] == "online"):
                self.alphaonl[s.id,c_id].ub = 1
                self.alphaonl[s.id,c_id].lb = 1
                self.alphainp[s.id,c_id].ub = 0
                self.alphainp[s.id,c_id].lb = 0
                if(s.mode_preference == 1):
                    self.tau[s.id,c_id].ub = 1
                    self.tau[s.id,c_id].lb = 1
                else:
                    self.tau[s.id,c_id].ub = 0
                    self.tau[s.id,c_id].lb = 0
            else:
                self.alphaonl[s.id,c_id].ub = 0
                self.alphaonl[s.id,c_id].lb = 0
                self.alphainp[s.id,c_id].ub = 1
                self.alphainp[s.id,c_id].lb = 1
                if(s.mode_preference == -1):
                    self.tau[s.id,c_id].ub = 1
                    self.tau[s.id,c_id].lb = 1
                else:
                    self.tau[s.id,c_id].ub = 0
                    self.tau[s.id,c_id].lb = 0
        # Fixing the betas and gammas
        for c_id in classes_for_student:
            # Getting class object
            for c_check in self.P.classes:
                if(c_check.id == c_id):
                    c = c_check
                    break 
            # Fixing elements
            if(c_id not in list(attended_classes.keys())):    
                for t in c.timesets:
                    self.betaonl[s.id,c_id,t].ub = 0
                    self.betaonl[s.id,c_id,t].lb = 0
                    self.betainp[s.id,c_id,t].ub = 0
                    self.betainp[s.id,c_id,t].lb = 0
                    for r in c.rooms:
                        self.gamma[s.id,c_id,t,r,t].ub = 0
                        self.gamma[s.id,c_id,t,r,t].lb = 0
            else:
                # Getting properties of solution
                for c_sol in solution:
                    if(c_sol.attrib['id'] == c_id):
                        # Locations
                        room = c_sol.attrib['room']
                        # Timeset
                        days = c_sol.attrib['online']
                        start = c_sol.attrib['start']
                        length = c_sol.attrib['length']
                        weeks = c_sol.attrib['weeks']
                        for t in self.P.timesets:
                            if(t.days == days and
                            t.start == start and
                            t.length == length and
                            t.weeks == weeks):
                                timeset = t.id
                        break
                # Fixing the variables
                for t in c.timesets:
                    if(timeset != t):
                        self.betaonl[s.id,c_id,t].ub = 0
                        self.betaonl[s.id,c_id,t].lb = 0
                        self.betainp[s.id,c_id,t].ub = 0
                        self.betainp[s.id,c_id,t].lb = 0
                        for r in c.rooms:
                            self.gamma[s.id,c_id,t,r,t].ub = 0
                            self.gamma[s.id,c_id,t,r,t].lb = 0
                    else:
                        if(attended_classes[c_id] == "online"):
                            self.betaonl[s.id,c_id,t].ub = 1
                            self.betaonl[s.id,c_id,t].lb = 1
                            self.betainp[s.id,c_id,t].ub = 0
                            self.betainp[s.id,c_id,t].lb = 0
                            for r in c.rooms:
                                if(r == 0):
                                    self.gamma[s.id,c_id,t,r,t].ub = 1
                                    self.gamma[s.id,c_id,t,r,t].lb = 1
                                else:
                                    self.gamma[s.id,c_id,t,r,t].ub = 0
                                    self.gamma[s.id,c_id,t,r,t].lb = 0
                        else:
                            self.betaonl[s.id,c_id,t].ub = 0
                            self.betaonl[s.id,c_id,t].lb = 0
                            self.betainp[s.id,c_id,t].ub = 1
                            self.betainp[s.id,c_id,t].lb = 1
                            for r in c.rooms:
                                if(r == room):
                                    self.gamma[s.id,c_id,t,r,t].ub = 1
                                    self.gamma[s.id,c_id,t,r,t].lb = 1
                                else:
                                    self.gamma[s.id,c_id,t,r,t].ub = 0
                                    self.gamma[s.id,c_id,t,r,t].lb = 0
        # Fixing the h variables
        class_pair_combos = itertools.combinations(classes_for_student, 2)
        for pair in class_pair_combos:
            # If one (or both) of the classes is not attended then no conflict
            if(pair[0] not in list(attended_classes.keys()) or pair[1] not in list(attended_classes.keys())):
                if(pair[0] < pair[1]):
                    self.h[s.id,pair[0],pair[1]].ub = 0
                    self.h[s.id,pair[0],pair[1]].lb = 0
                else:
                    self.h[s.id,pair[1],pair[0]].ub = 0
                    self.h[s.id,pair[1],pair[0]].lb = 0
                continue
            # Getting properties of solution
            for c_sol in solution:
                if(c_sol.attrib['id'] == pair[0]):
                    # Locations
                    room1 = c_sol.attrib['room']
                    # Timeset
                    days = c_sol.attrib['online']
                    start = c_sol.attrib['start']
                    length = c_sol.attrib['length']
                    weeks = c_sol.attrib['weeks']
                    for t in self.P.timesets:
                        if(t.days == days and
                        t.start == start and
                        t.length == length and
                        t.weeks == weeks):
                            timeset1 = t.id
                if(c_sol.attrib['id'] == pair[1]):
                    # Locations
                    room2 = c_sol.attrib['room']
                    # Timeset
                    days = c_sol.attrib['online']
                    start = c_sol.attrib['start']
                    length = c_sol.attrib['length']
                    weeks = c_sol.attrib['weeks']
                    for t in self.P.timesets:
                        if(t.days == days and
                        t.start == start and
                        t.length == length and
                        t.weeks == weeks):
                            timeset2 = t.id
            # Check if the timesets overlap, if they do then set variables
            t1 = self.P.timesets[timeset1]
            t2 = self.P.timesets[timeset2]
            if(fn.timesetOverlapCheck(t1,t2) == True):
                if(pair[0] < pair[1]):
                    self.h[s.id,pair[0],pair[1]].ub = 1
                    self.h[s.id,pair[0],pair[1]].lb = 1
                else:
                    self.h[s.id,pair[1],pair[0]].ub = 1
                    self.h[s.id,pair[1],pair[0]].lb = 1
                continue
            # Checking how the student is attending so we know where student is
            if(attended_classes[pair[0]] == "online"):
                student_room1 = 0
            else:
                student_room1 = room1
            if(attended_classes[pair[1]] == "online"):
                student_room2 = 0
            else:
                student_room2 = room2
            room_distance = self.P.weightedRoomAdjacency.distance(student_room1,student_room2)
            time_distance = self.P.distribution_arrays['InteriorDistance'][timeset1,timeset2]
            # Check if the travel time between rooms is greater than the time available
            if(time_distance < room_distance):
                if(pair[0] < pair[1]):
                    self.h[s.id,pair[0],pair[1]].ub = 1
                    self.h[s.id,pair[0],pair[1]].lb = 1
                else:
                    self.h[s.id,pair[1],pair[0]].ub = 1
                    self.h[s.id,pair[1],pair[0]].lb = 1
                continue
            else:
                if(pair[0] < pair[1]):
                    self.h[s.id,pair[0],pair[1]].ub = 0
                    self.h[s.id,pair[0],pair[1]].lb = 0
                else:
                    self.h[s.id,pair[1],pair[0]].ub = 0
                    self.h[s.id,pair[1],pair[0]].lb = 0


    """
    Function to set an objective or fix an objective at a certain value
    """

    # Function to convert a string into the relevant objective function
    def objective_string2gurobi(self,z):
        if(z == "ModuleRequest"):
            z_new = self.objective_module_requests()
        elif(z == "ModePreferences"):
            z_new = self.objective_mode_preference()
        elif(z == "StudentConflicts"):
            z_new = self.objective_student_conflict()
        elif(z == "RoomPenalty"):
            z_new = self.objective_room_penalty()
        elif(z == "TimesetPenalty"):
            z_new = self.objective_timeset_penalty()
        elif(z == "RoomUsage"):
            z_new = self.objective_room_usage()
        elif(z == "TimesetUsage"):
            z_new = self.objective_timeset_usage()
        elif(z == "Switches"):
            z_new = self.objective_switches()
        else:
            z_new = LinExpr()
        return z_new
    
    # Sets the objective function
    def set_objective(self,z,sense = "Minimise"):
        z_gc = self.objective_string2gurobi(z)
        if(sense == "Maximise"):
            self.M.setObjective(z_gc, GRB.MAXIMIZE)
        else:
            self.M.setObjective(z_gc, GRB.MINIMIZE)
        self.M.update()

    # Fixes an objective function at a certain value
    def constrain_objective(self,z,value,sense = "Minimise"):
        z_gc = self.objective_string2gurobi(z)
        if(sense == "Maximise"):
            self.M.addConstr(z_gc >= value, name="objective_fix_"+str(z))
        elif(sense == "Minimise"):
            self.M.addConstr(z_gc <= value, name="objective_fix_"+str(z))
        else:   
            self.M.addConstr(z_gc == value, name="objective_fix_"+str(z))
        self.M.update()
    
    # Unfixes an objective function  
    def unconstrain_last_objective(self,z):
        self.M.remove(self.M.getConstrByName("objective_fix_"+str(z)))
        self.M.update()

    # Get objective value
    def objective_value(self):
        obj = self.M.getObjective()
        return obj.getValue()
    
    """
    Base model objectives
    """
    
    # Maximise requested courses
    def objective_module_requests(self):
        z = LinExpr()
        for s in self.P.students:
            for k in s.modules:
                if(k not in s.required_modules):
                    z.add(self.n[s.id,k])
        return z
    
    # Maximise alignment with preferences
    def objective_mode_preference(self):
        z = LinExpr()
        for s in self.P.students:
            for k in self.P.modules:
                if(k.id in s.modules):
                    for f in k.configs:
                        for p in f.subparts:
                            for c in self.P.classes:
                                if(c.id in p.classes):
                                    z.add(1*self.tau[s.id,c.id])
        return z
    
    # Minimise conflicts
    def objective_student_conflict(self):
        z = LinExpr()
        for s in self.P.students:
            classes_for_student = []
            for k in self.P.modules:
                if(k.id in s.modules):
                    for f in k.configs:
                        for p in f.subparts:
                            for c in self.P.classes:
                                if(c.id in p.classes):
                                    classes_for_student.append(c.id)
            class_pair_combos = itertools.combinations(classes_for_student, 2)
            for pair in class_pair_combos:
                if(pair[0] < pair[1]):
                    z.add(self.h[s.id,pair[0],pair[1]])
                else:
                    z.add(self.h[s.id,pair[1],pair[0]])
        return z
    
    # Minimise room penalties
    def objective_room_penalty(self):
        z = LinExpr()
        for c in self.P.classes:
            for r in c.rooms:
                z.add(c.rooms[r]*self.yr[c.id,r])
        return z

    # Minimise timeset penalties
    def objective_timeset_penalty(self):
        z = LinExpr()
        for c in self.P.classes:
            for t in c.timesets:
                z.add(c.timesets[t]*self.yt[c.id,t])
        return z
    
    # Minimise total room usage
    def objective_room_usage(self):
        z = LinExpr()
        return z
    
    # Minimise timeset usage
    def objective_timeset_usage(self):
        z = LinExpr()
        return z

    # Minimise number of switches of mode
    def objective_switches(self):
        z = LinExpr()
        return z



    """
    

    CONSTRAINT ADDING FUNCTIONS


    """

    """
    Adding the base model constraints
    """

    def addBaseConstraints(self):
        self.addBase456()
        # Base 7 and 8 already considered by construction
        self.addBase9()
        self.addBase10()
        self.addBase1112()
        self.addBase13()
        self.addBase14()
        self.addBase1516()
        self.addBase17()
        self.addBase1819()
        self.addBase20()
        # Base 21 by construction
        self.addBase22()
        self.addBase23()
        # Base 24 by construction
        self.addBase2526()
        self.addBase27()
        self.addBase28()
        self.addBase29()
        self.addBase30()
        self.addBase3132()
        self.addBase33()
        self.addBase3435()
        # Base 36 to 44
        if(len(fn.intersection([36,37,38,39,40,41,42,43,44],self.inactive_constraints)) == 0):
            self.addBase36to44()
        # Base 45 to 53
        if(len(fn.intersection([36,37,38,39,40,41,42,43,44],self.inactive_constraints)) == 0):
            if(len(fn.intersection([45,46,47,48,49,51,52,53],self.inactive_constraints)) == 0):
                self.addBase45to53()
        # Update the model
        self.M.update()
        
    
    # Linking constraints for resource assignment 
    def addBase456(self):
        """
        This constraint links the x variables to the yr and yt variables.
        """
        # Check if need to include constraint
        if(fn.intersection([4,5,6],self.inactive_constraints)):
            return
        # Add constraint for all classes
        for c in self.P.classes:
            # Skip to next class if class is fixed
            if(self.fixed_elements != None):
                if(c.id in self.fixed_elements.classes):
                    continue
            # Add constraint for class
            for r in c.rooms:
                expression = quicksum(self.x[c.id,r,t] for t in c.timesets)
                self.M.addConstr(self.yr[c.id,r] == expression, name='cfour') # Constraint 4
            for t in c.timesets:
                expression = quicksum(self.x[c.id,r,t] for r in c.rooms)
                self.M.addConstr(self.yt[c.id,t] <= expression, name='cfive') # Constraint 5
                self.M.addConstr(expression <= 2*self.yt[c.id,t], name='csix') # Constraint 6


    # Resource compatiblity constraints
    def addBase9(self):
        """
        This constraint set ensures that resources used are compatible with each other.
        """
        # Check if need to include constraint
        if(fn.intersection([9],self.inactive_constraints)):
            return
        # Add constraint for all classes
        for c in self.P.classes:
            # Skip to next class if class is fixed
            if(self.fixed_elements != None):
                if(c.id in self.fixed_elements.classes):
                    continue
            # Add constraint for class 
            expression = LinExpr()
            for r in c.rooms:
                for t in c.timesets:
                    if(self.P.roomtimeCompatibility.compatible(r,t) == False):
                        expression.add(self.x[c.id,r,t])
            self.M.addConstr(expression == 0, name='cnine') # Constraint 9

  
    # Classes can only be assigned at most one timeset
    def addBase10(self):
        """
        This constraint ensures that a class is assigned at most one timeset
        """
        # Check if need to include constraint
        if(fn.intersection([10],self.inactive_constraints)):
            return
        # Add constraint for all classes
        for c in self.P.classes:
            # Skip to next class if class is fixed
            if(self.fixed_elements != None):
                if(c.id in self.fixed_elements.classes):
                    continue
            # Add constraint for class 
            self.M.addConstr(quicksum(self.yt[c.id,t] for t in c.timesets) <= 1, name='cten')


    # Classes can only be assigned a maximum of two teaching spaces
    def addBase1112(self):
        """
        Due to the nature of hybrid teaching
        classes can only be assigned a maximum of two teaching spaces
        """
        # Check if need to include constraint
        if(fn.intersection([11,12],self.inactive_constraints)):
            return
        # Add constraint for all classes
        for c in self.P.classes:
            # Skip to next class if class is fixed
            if(self.fixed_elements != None):
                if(c.id in self.fixed_elements.classes):
                    continue
            # Add constraint for class
            self.M.addConstr(quicksum(self.yr[c.id,r] for r in c.rooms if r != 0) <= 1, name='celeven')
            self.M.addConstr(quicksum(self.yr[c.id,r] for r in c.rooms) <= 2, name='ctwelve')


    # Classes can happen online and in-person if the physical room is appropriate
    def addBase13(self):
        """
        Constraint prevents hybrid teaching in classes that cannot host hybrid teaching
        """
        # Check if need to include constraint
        if(fn.intersection([13],self.inactive_constraints)):
            return
        R_minus_h_r = [r.id for r in self.P.rooms if r.hybridcapable == False]
        # Add constraint for all classes
        for c in self.P.classes:
            # Skip to next class if class is fixed
            if(self.fixed_elements != None):
                if(c.id in self.fixed_elements.classes):
                    continue
            # Add constraint for class
            if(0 in [r.id for r in self.P.rooms]):
                expression = quicksum(self.yr[c.id,r_id] for r_id in fn.intersection(c.rooms,R_minus_h_r))
                self.M.addConstr(self.yr[c.id,0] <= 1 - expression, name='cthirteen')


    # In-person classes should not use the same teaching space at the same time (time consuming)
    def addBase14(self):
        """
        Checking rooms and overlapping timeslots to ensure that a physical
        room isn't being used by two classes at once.
        """
        # Check if need to include constraint
        if(fn.intersection([14],self.inactive_constraints)):
            return
        # Adding the constraint
        for r in self.P.rooms:
            if(r.id != 0):
                for overlaps in self.P.timesetoverlaps:
                    expression = LinExpr()
                    for c in self.P.classes:
                        if(r.id in c.rooms):
                            for t in overlaps:
                                if(t in c.timesets):
                                    expression.add(self.x[c.id,r.id,t])
                    self.M.addConstr(expression <= 1, name='cfourteen')

                    
    # Module is offered if at least one configuration is offered
    def addBase1516(self):
        """
        Offering a module if at least one configuration is offered
        """
        # Check if need to include constraint
        if(fn.intersection([15,16],self.inactive_constraints)):
            return
        # Adding constraint
        for k in self.P.modules:
            len_FK = len(k.configs)
            expression = quicksum(self.q[k.id,f.id] for f in k.configs)
            self.M.addConstr(self.g[k.id]*len_FK >= expression, name='cfifteen')
            self.M.addConstr(self.g[k.id] <= expression, name='csixteen')


    # Configuration is offered if and only if every subpart is offered
    def addBase17(self):
        """
        Configuration offered if and only if every subpart is offered
        """
        # Check if need to include constraint
        if(fn.intersection([17],self.inactive_constraints)):
            return
        # Adding constraint
        for k in self.P.modules:
            for f in k.configs:
                len_PFK = len(f.subparts)
                expression = quicksum(self.w[k.id,f.id,p.id] for p in f.subparts)
                self.M.addConstr(len_PFK*self.q[k.id,f.id] == expression, name='cseventeen')


    # Subpart is offered if at least one class in the subpart is offered
    def addBase1819(self):
        """
        Subparts are offered if at least one class in the subpart is offered
        """
        # Check if need to include constraint
        if(fn.intersection([18,19],self.inactive_constraints)):
            return
        # Adding constraint
        for k in self.P.modules:
            for f in k.configs:
                for p in f.subparts:
                    len_T = len(self.P.timesets)
                    len_R = len(self.P.rooms)
                    len_CPFK = len(p.classes)
                    expression = LinExpr()
                    for c_id in p.classes:
                        for c in self.P.classes:
                            if(c.id == c_id):
                                for r in c.rooms:
                                    for t in c.timesets:
                                        expression.add(self.x[c.id,r,t])
                    self.M.addConstr(self.w[k.id,f.id,p.id]*len_T*len_CPFK*len_R >= expression, name='ceighteen')
                    self.M.addConstr(self.w[k.id,f.id,p.id] <= expression, name='cnineteen')                
    
    
    # Student does not attend a module that is not offered
    def addBase22(self):
        """
        Student cannot attend a module that isn't happening
        """
        # Check if need to include constraint 
        if(fn.intersection([22],self.inactive_constraints)):
            return
        # Adding constraint
        for s in self.P.students:
            for k_id in s.modules:
                self.M.addConstr(self.n[s.id,k_id] <= self.g[k_id], name='ctwentytwo')
                

    # Student must attend all compulsory modules
    def addBase23(self):
        """
        All compulsory modules need to be attended
        """
        # Check if need to include constraint 
        if(fn.intersection([23],self.inactive_constraints)):
            return
        # Adding constraint
        for s in self.P.students:
            for k_id in s.required_modules:
                self.M.addConstr(self.n[s.id,k_id] == 1, name='ctwentythree')


    # Student does not attend a class that is not offered
    def addBase2526(self):
        """
        Student doesn't attend a class that isn't offered
        """
        # Check if need to include constraint 
        if(fn.intersection([25,26],self.inactive_constraints)):
            return
        # Adding constraint
        for s in self.P.students:
            classes_for_student = []
            for k in self.P.modules:
                if(k.id in s.modules):
                    for f in k.configs:
                        for p in f.subparts:
                            for c in self.P.classes:
                                if(c.id in p.classes):
                                    classes_for_student.append(c)
            for c in classes_for_student:
                # 25
                summation = LinExpr()
                for r in c.rooms:
                    if(r != 0):
                        for t in c.timesets:
                            summation.add(self.x[c.id,r,t])
                self.M.addConstr(self.alphainp[s.id,c.id] <= summation, name='ctwentyfive')
                # 26
                if(0 in c.rooms):
                    expression = quicksum(self.x[c.id,0,t] for t in c.timesets)
                    self.M.addConstr(self.alphaonl[s.id,c.id] <= expression, name='ctwentysix')
                
    # Student attends a module if they attend a configuration for that module
    def addBase27(self):
        """
        Student attends module if they attend a configuration for that module
        """
        # Check if need to include constraint 
        if(fn.intersection([27],self.inactive_constraints)):
            return
        # Adding constraint
        for s in self.P.students:
            for k in self.P.modules:
                if(k.id in s.modules):
                    summation = quicksum(self.m[s.id,k.id,f.id] for f in k.configs)
                    self.M.addConstr(summation == self.n[s.id,k.id], name='ctwentyseven')
    

    # Student attends a configuration if they attend a class from each subpart  
    def addBase28(self):
        """
        Student is assigned a configuration if they attend a class from each subpart
        """
        # Check if need to include constraint 
        if(fn.intersection([28],self.inactive_constraints)):
            return
        # Adding constraint            
        for s in self.P.students:
            for k in self.P.modules:
                if(k.id in s.modules):
                    for f in k.configs:
                        len_PFK = len(f.subparts)
                        summation = quicksum(self.b[s.id,k.id,f.id,c.id] for c in f.subparts)
                        self.M.addConstr(summation == len_PFK*self.m[s.id,k.id,f.id], name='ctwentyeight')
    

    # Student has at most one class from a subpart and doesn't attend subpart if no classes attended
    def addBase29(self):
        """
        Student has at most one class from a subpart
        """
        # Check if need to include constraint 
        if(fn.intersection([29],self.inactive_constraints)):
            return
        # Adding constraint  
        for s in self.P.students:
            for k in self.P.modules:
                if(k.id in s.modules):
                    for f in k.configs:
                        for p in f.subparts:
                            summation = quicksum(self.a[s.id,k.id,f.id,p.id,c_id] for c_id in p.classes)
                            self.M.addConstr(summation == self.b[s.id,k.id,f.id,p.id], name='ctwentynine')
   

    # Student attends either the online version or the in-person class (or neither)
    def addBase30(self):
        """
        Student attends online or inperson or neither
        """
        # Check if need to include constraint 
        if(fn.intersection([30],self.inactive_constraints)):
            return
        # Adding constraint
        for s in self.P.students:
            for k in self.P.modules:
                if(k.id in s.modules):
                    for f in k.configs:
                        for p in f.subparts:
                            for c_id in p.classes:
                                alphasum = self.alphaonl[s.id,c_id] + self.alphainp[s.id,c_id]
                                self.M.addConstr(self.a[s.id,k.id,f.id,p.id,c_id] == alphasum, name='cthirty')
    

    # Room capacity constraints and class subcription constraints 
    def addBase3132(self):
        """
        In the problem there are two capacities:
        - Room capacity
        - Subscription capacity
        """
        # Check if need to include constraint 
        if(fn.intersection([31,32],self.inactive_constraints)):
            return
        # Adding constraint
        for k in self.P.modules:
            for f in k.configs:
                for p in f.subparts:
                    for c_id in p.classes:
                        # Identifying students that could attend
                        student_id_list = []
                        for s in self.P.students:
                            if(k.id in s.modules):
                                student_id_list.append(s.id)
                        # Retrieving class from id
                        for c_check in self.P.classes:
                            if(c_check.id == c_id):
                                c = c_check
                                break
                        # Finding out what physical rooms the class can happen in
                        room_id_cap_list = []
                        for r in self.P.rooms:
                            if(r.id != 0 and r.id in c.rooms):
                                room_id_cap_list.append((r.id,r.capacity))
                        # Maximum physical attendance constraint
                        max_attendance = quicksum(r_id_cap[1]*self.yr[c.id,r_id_cap[0]] for r_id_cap in room_id_cap_list)
                        total_inperson_attendance = quicksum(self.alphainp[s_id,c.id] for s_id in student_id_list)
                        self.M.addConstr(total_inperson_attendance <= max_attendance, name='cthirtyone')
                        # Subscription limit constraints
                        total_attendance = quicksum(self.alphainp[s_id,c.id] + self.alphaonl[s_id,c.id] for s_id in student_id_list)
                        self.M.addConstr(total_attendance <= c.sub_limit, name='cthirtytwo')
    
    # Parent child classes
    def addBase33(self):
        """
        If a student attends a child class then they
        must attend a parent class if one exists.
        """
        # Check if need to include constraint 
        if(fn.intersection([33],self.inactive_constraints)):
            return
        # Adding constraint
        for s in self.P.students:
            for k in self.P.modules:
                if(k.id in s.modules):
                    for f in k.configs:
                        for p in f.subparts:
                            for c in self.P.classes:
                                if(c.id in p.classes):
                                    if(c.parent != None):
                                        alpha_child = self.alphainp[s.id,c.id] + self.alphaonl[s.id,c.id]
                                        alpha_parent = self.alphainp[s.id,c.parent] + self.alphaonl[s.id,c.parent]
                                        self.M.addConstr(alpha_child <= alpha_parent, name='cthirtythree')

    
    # Mode request constraints
    def addBase3435(self):
        """
        Linking the mode request variables to attendance variables
        """
        # Check if need to include constraint 
        if(fn.intersection([34,35],self.inactive_constraints)):
            return
        # Adding constraint
        for s in self.P.students:
            pi_value = s.mode_preference
            for k in self.P.modules:
                if(k.id in s.modules):
                    for f in k.configs:
                        for p in f.subparts:
                            for c in self.P.classes:
                                if(c.id in p.classes):
                                    self.M.addConstr(self.tau[s.id,c.id] >= pi_value*(self.alphaonl[s.id,c.id] - self.alphainp[s.id,c.id]), name='cthirtyfour')
                                    self.M.addConstr(self.tau[s.id,c.id] <= self.alphaonl[s.id,c.id] + self.alphainp[s.id,c.id], name='cthirtyfive')

        
    # Detection of if student has overlapping class
    def addBase36to44(self):
        print("Adding student overlap constraints")
        D_array_sameattendee = self.P.distribution_arrays["InteriorDistance"]
        for s in self.P.students:
            # Check if need to skip student
            if(self.fixed_elements != None):
                if(s.id in self.fixed_elements.students):
                    continue
            # Add the constraints linking attendance with beta variables
            classes_for_student = []
            for k in self.P.modules:
                if(k.id in s.modules):
                    for f in k.configs:
                        for p in f.subparts:
                            for c in self.P.classes:
                                if(c.id in p.classes):
                                    classes_for_student.append(c.id)
                                    for t in c.timesets:
                                        self.M.addConstr(self.betainp[s.id,c.id,t] <= self.alphainp[s.id,c.id]).Lazy = 1 # 39
                                        self.M.addConstr(self.betaonl[s.id,c.id,t] <= self.alphaonl[s.id,c.id]).Lazy = 1 # 40
                                        self.M.addConstr(self.betainp[s.id,c.id,t] <= self.yt[c.id,t]).Lazy = 1 # 41
                                        self.M.addConstr(self.betaonl[s.id,c.id,t] <= self.yt[c.id,t]).Lazy = 1 # 42
                                        self.M.addConstr(self.betainp[s.id,c.id,t] >= self.alphainp[s.id,c.id] + self.yt[c.id,t] - 1).Lazy = 1 # 43
                                        self.M.addConstr(self.betaonl[s.id,c.id,t] >= self.alphaonl[s.id,c.id] + self.yt[c.id,t] - 1).Lazy = 1 #44
            # Connecting the beta variables to the penalty variables
            class_pair_combos = itertools.combinations(classes_for_student, 2)
            for pair in class_pair_combos:
                # Getting the class objects
                for c_check in self.P.classes:
                    if(c_check.id == pair[0]):
                        c1 = c_check
                    if(c_check.id == pair[1]):
                        c2 = c_check
                # Checking if the two classes can ever have a scheduling issue
                if(fn.skip_student_scheduling_issues(c1,c2) == True):
                    continue
                # Only consider overlapping timesets
                params = list(itertools.product(c1.timesets, c2.timesets))
                for t_p in itertools.filterfalse(lambda t: D_array_sameattendee[t[0],t[1]] >= 0, params):
                    t1_id = t_p[0]
                    t2_id = t_p[1]
                    expression = self.betainp[s.id,c1.id,t1_id] + self.betaonl[s.id,c1.id,t1_id] + self.betainp[s.id,c2.id,t2_id] + self.betaonl[s.id,c2.id,t2_id]
                    if(pair[0] < pair[1]):
                        self.M.addConstr(expression <= 1 + self.h[s.id,pair[0],pair[1]]).Lazy = 1 # 38
                    else:
                        self.M.addConstr(expression <= 1 + self.h[s.id,pair[1],pair[0]]).Lazy = 1 # 38
                    
        
    # Detection if a student has enough travel time between classes
    def addBase45to53(self):
        print("Adding student travel time constraints")
        D_array_sameattendee = self.P.distribution_arrays["InteriorDistance"]
        for s in self.P.students:
            # Check if need to skip student
            if(self.fixed_elements != None):
                if(s.id in self.fixed_elements.students):
                    continue
            # Add the constraints linking attendance with gamma variables
            classes_for_student = []
            for k in self.P.modules:
                if(k.id in s.modules):
                    for f in k.configs:
                        for p in f.subparts:
                            for c in self.P.classes:
                                if(c.id in p.classes):
                                    classes_for_student.append(c.id)
                                    for t in c.timesets:
                                        for r in c.rooms:
                                            if(r == 0):
                                                self.M.addConstr(self.gamma[s.id,c.id,r,t] <= self.betaonl[s.id,c.id,t]).Lazy = 1
                                                self.M.addConstr(self.gamma[s.id,c.id,r,t] <= self.yr[c.id,r]).Lazy = 1
                                                self.M.addConstr(self.gamma[s.id,c.id,r,t] >= self.betaonl[s.id,c.id,t] + self.yr[c.id,r] - 1).Lazy = 1
                                            else:
                                                self.M.addConstr(self.gamma[s.id,c.id,r,t] <= self.betainp[s.id,c.id,t]).Lazy = 1
                                                self.M.addConstr(self.gamma[s.id,c.id,r,t] <= self.yr[c.id,r]).Lazy = 1
                                                self.M.addConstr(self.gamma[s.id,c.id,r,t] >= self.betainp[s.id,c.id,t] + self.yr[c.id,r] - 1).Lazy = 1      
            # Connecting gamma variables to penalty terms
            class_pair_combos = itertools.combinations(classes_for_student, 2)
            for pair in class_pair_combos:
                # Getting the class objects
                for c_check in self.P.classes:
                    if(c_check.id == pair[0]):
                        c1 = c_check
                    if(c_check.id == pair[1]):
                        c2 = c_check
                # Checking if the two classes can ever have a scheduling issue
                if(fn.skip_student_scheduling_issues(c1,c2) == True):
                    continue
                # Further checks
                maximum_travel_distance = fn.max_travel_distance(self.P,c1,c2)
                # Only consider timesets that don't overlap
                params = list(itertools.product(c1.timesets, c2.timesets))
                params2 = list(itertools.filterfalse(lambda t: D_array_sameattendee[t[0],t[1]] < 0, params))
                # Remove timesets with a spacing greater than max travel time between two possible rooms
                for t_p in itertools.filterfalse(lambda t: D_array_sameattendee[t[0],t[1]] > maximum_travel_distance, params2):
                    t1_id = t_p[0]
                    t2_id = t_p[1]
                    for r1 in c1.rooms:
                        for r2 in c2.rooms:
                            if(self.P.weightedRoomAdjacency.distance(r1,r2) > D_array_sameattendee[t1_id,t2_id]):
                                if(pair[0] < pair[1]):
                                    self.M.addConstr(self.gamma[s.id,c1.id,r1,t1_id] + self.gamma[s.id,c2.id,r2,t2_id] <= 1 + self.h[s.id,pair[0],pair[1]]).Lazy = 1
                                else:
                                    self.M.addConstr(self.gamma[s.id,c1.id,r1,t1_id] + self.gamma[s.id,c2.id,r2,t2_id] <= 1 + self.h[s.id,pair[1],pair[0]]).Lazy = 1
    

    # Staff must be able to attend classes they can teach (time consuming)
    def addBase20(self):
        # Check if need to include constraint
        if(fn.intersection([20],self.inactive_constraints)):
            return
        # Adding constraint
        for dist in self.P.distributions:
            if(dist.required == True and dist.type == "SameAttendees"):
                class_pair_combos = itertools.combinations(dist.classes, 2)
                for pair in class_pair_combos:
                    if(self.fixed_elements != None):
                        if(pair[0] not in self.fixed_elements.classes or pair[0] not in self.fixed_elements.classes):
                            # Neither are fixed
                            if(pair[0] not in self.fixed_elements.classes and pair[0] not in self.fixed_elements.classes):
                                self.addSameAttendeeNoneFixed(pair[0],pair[1])
                            # Pair 0 is fixed
                            elif(pair[0] not in self.fixed_elements.classes):
                                self.addSameAttendeeOneFixed(pair[0],pair[1])
                            # Pair 1 is fixed
                                self.addSameAttendeeOneFixed(pair[1],pair[0])
                    else:
                        self.addSameAttendeeNoneFixed(pair[0],pair[1])
    
    # One fixed and one unfixed
    def addSameAttendeeOneFixed(self,fixed,unfixed):
        # Retrieving details of fixed class
        solution = self.solution
        # Check if class has an allocation at all
        timeset = None
        room = None
        online = None
        for c_sol in solution:
            if(c_sol.attrib['id'] == fixed):
                # Locations
                room = c_sol.attrib['room']
                online = c_sol.attrib['online']
                # Timeset
                days = c_sol.attrib['online']
                start = c_sol.attrib['start']
                length = c_sol.attrib['length']
                weeks = c_sol.attrib['weeks']
                for t in self.P.timesets:
                    if(t.days == days and
                       t.start == start and
                       t.length == length and
                       t.weeks == weeks):
                        timeset = t.id
                break
        # If fixed class has no allocation then pass
        if(timeset == None):
            return
        # Getting the class objects
        for c_check in self.P.classes:
            if(c_check.id == fixed):
                c1 = c_check
            if(c_check.id == unfixed):
                c2 = c_check
        # Getting the relevant arrays
        D_array_sameattendee = self.P.distribution_arrays["InteriorDistance"]
        maximum_travel_distance = fn.max_travel_distance(self.P,c1,c2)
        # Looping through elements of unfixed
        for t in c2.timesets:
            if(D_array_sameattendee[timeset,t] <= maximum_travel_distance):
                if(D_array_sameattendee[timeset,t] >= 0):
                    for r in c2.rooms:
                        if(room != None):
                            if(self.P.weightedRoomAdjacency.distance(room,r) > D_array_sameattendee[timeset,t]):
                                self.M.addConstr(self.x[c2.id,r,t] <= 0, name='ctwentyonefix')
                        if(online == True):
                            if(self.P.weightedRoomAdjacency.distance(0,r) > D_array_sameattendee[timeset,t]):
                                self.M.addConstr(self.x[c2.id,r,t] <= 0, name='ctwentyonefix')
                else:
                    self.M.addConstr(self.yt[c2.id,t] <= 0, name='ctwentyonefix').Lazy = 1


    # None fixed for sameattendee   
    def addSameAttendeeNoneFixed(self,unfixed1,unfixed2):
        # Getting the class objects
        for c_check in self.P.classes:
            if(c_check.id == unfixed1):
                c1 = c_check
            if(c_check.id == unfixed2):
                c2 = c_check
        # Getting the relevant arrays
        D_array_sameattendee = self.P.distribution_arrays["InteriorDistance"]
        maximum_travel_distance = fn.max_travel_distance(self.P,c1,c2)
        # Remove pairs of timesets with a spacing greater than max travel time between two possible rooms
        params = list(itertools.product(c1.timesets, c2.timesets))
        for t_p in itertools.filterfalse(lambda t: D_array_sameattendee[t[0],t[1]] > maximum_travel_distance, params):
            t1 = t_p[0]
            t2 = t_p[1]
            # Checking if the times overlap
            if(D_array_sameattendee[t1,t2] >= 0):
                for r1 in c1.rooms:
                    for r2 in c2.rooms:
                        if(self.P.weightedRoomAdjacency.distance(r1,r2) > D_array_sameattendee[t1,t2]):
                            self.M.addConstr(self.x[c1.id,r1,t1] + self.x[c2.id,r2,t2] <= 1, name='ctwentynonefix').Lazy = 1
            else:
               self.M.addConstr(self.yt[c1.id,t1] + self.yt[c2.id,t2] <= 1, name='ctwentynonefix').Lazy = 1
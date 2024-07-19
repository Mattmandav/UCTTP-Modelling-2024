# External packages
import argparse
import pickle
import pandas as pd

# Local packages
import functions as fn
import instance as inst
from milp_model_construction import ModelObject
from milp_model_solve import LexicographicOnly
import xml.etree.ElementTree as ET

"""
Importing arguments
"""

parser = argparse.ArgumentParser(description='UCTTP driver file')


# Filename of instance
parser.add_argument('--filename', type=str, default = 'wbg-fal10',
                    help='Filename of the instance stored in data folder (default = wbg-fal10)')
# Do not add a dummy to instance
parser.add_argument('--nodummy',action='store_true',
                    help='Do not build an instance with a dummy room')
# Do not add a dummy to instance
parser.add_argument('--reset',action='store_true',
                    help='Overwrite the previously saved instances if found')


# Student count
parser.add_argument('--studentcount', type=int, default = None,
                    help='Number of students to be kept in the instance (default = All)')
# Student count start point
parser.add_argument('--studentstart', type=int, default = 1,
                    help='The student that we start the student count from (default = 1)')
# Online space distance
parser.add_argument('--onlinedist', type=float, default = 1.5,
                    help='Distance that the online space is away from physical space (default = 1.5)')
# Online space distance
parser.add_argument('--roomcapreduction', type=float, default = 75,
                    help='Percentage decrease in room capacity e.g. 75 is a four-fold reduction (default = 75)')


# Timelimit for solver
parser.add_argument('--timelimit', type=int, default = None,
                    help='Time limit for the solver (default = None)')
# Number of cores for solver
parser.add_argument('--solvercores', type=int, default = None,
                    help='Number of cores the solver can use (default = All)')
# Number of cores for solver
parser.add_argument('--solvernodefile', type=int, default = 1,
                    help='Memory in GB before solver creates nodefile (default = 1)')


args = parser.parse_args()
args.dummy = not args.nodummy

"""
Importing the instance
"""

P = fn.instanceImport(filename=args.filename,
                      dummyRoomPenaltyScaling=1,
                      dummyRoomDistanceScaling=args.onlinedist, 
                      addDummy=args.dummy, 
                      force_reset=args.reset)

"""
Modifying the instance
"""

# Thinning the number of students
P.remove_students(count=args.studentcount,start=args.studentstart)
# Decreasing room capacity
P.reduce_capacity(args.roomcapreduction)
# Setting student preferences
P.student_preferences(proportion=(1,1,1))

"""
Applying a method
"""

LexModel = LexicographicOnly(P,args.solvercores,args.solvernodefile)
objective_list = [("ModuleRequest","Maximise"),("ModePreferences","Minimise"),("StudentConflicts","Minimise")]
#objective_list = [("ModuleRequest","Maximise"),("ModePreferences","Minimise")]
results = LexModel.lexicographic_solve(objective_list)
for ordering in results:
    print(ordering,results[ordering][0],results[ordering][1])
   
    
"""
Exporting the raw solutions
"""

outfile = open("output/"+str(args.filename)+"_dumped","wb")
pickle.dump(results, outfile)
outfile.close()


"""
Paper style export of results
"""

# Table 4
table4 = pd.DataFrame(data={"Instance":[P.filename],
                            "Students":[len(P.students)],
                            "Modules":[len(P.modules)],
                            "Classes":[len(P.classes)],
                            "Timesets":[len(P.timesets)],
                            "Rooms":[len(P.rooms)],
                            "Hybrid":[fn.hybrid_capable_count(P)]})
table4.to_csv("output/"+str(args.filename)+"_table4.csv", index=False)

# Table 5
table5 = pd.DataFrame(data={"Ordering":[],
                            "Z1":[],"Z2":[],"Z3":[],
                            "Total":[],"IP":[],"ONL":[],
                            "Switch":[]})
for ordering in results:
    new_row = {"Ordering": ordering,
                "Z1":results[ordering][0]["ModuleRequest"],
                "Z2":results[ordering][0]["ModePreferences"],
                "Z3":results[ordering][0]["StudentConflicts"],
                "Total":fn.attendance_breakdown(results[ordering][1])["total"],
                "IP":fn.attendance_breakdown(results[ordering][1])["inperson"],
                "ONL":fn.attendance_breakdown(results[ordering][1])["online"],
                "Switch":fn.switch_detection(results[ordering][1])["total"]}
    table5 = pd.concat([table5, pd.DataFrame([new_row])], ignore_index=True)
table5.to_csv("output/"+str(args.filename)+"_table5.csv", index=False)

# Table 6
data_prep = {"Ordering":[],"Measure":[]}
for s in P.students:
    data_prep[s.id] = []
table6 = pd.DataFrame(data=data_prep)
for ordering in results:
    solution_for_order = results[ordering][1]
    # Adding the electives
    new_row = {"Ordering": ordering, "Measure": "Electives"}
    new_row.update(fn.elective_breakdown(P,solution_for_order))
    table6 = pd.concat([table6, pd.DataFrame([new_row])], ignore_index=True)
    # Adding the conflicts
    new_row = {"Ordering": ordering, "Measure": "Conflict"}
    new_row.update(fn.conflict_breakdown(P,solution_for_order))
    table6 = pd.concat([table6, pd.DataFrame([new_row])], ignore_index=True)
    # Adding the mode
    new_row = {"Ordering": ordering, "Measure": "Mode"}
    new_row.update(fn.mode_breakdown(P,solution_for_order))
    table6 = pd.concat([table6, pd.DataFrame([new_row])], ignore_index=True)
table6.to_csv("output/"+str(args.filename)+"_table6.csv", index=False)

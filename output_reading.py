# External packages
import argparse
import pandas as pd

"""
Getting arguments
"""

parser = argparse.ArgumentParser(description='UCTTP driver file')

# Filename of instance
parser.add_argument('--filename', type=str, default = 'wbg-fal10',
                    help='Filename of the instance stored in data folder (default = wbg-fal10)')

args = parser.parse_args()

"""
Importing data
"""

data = pd.read_csv('output/'+str(args.filename)+'_table6.csv')
#print(data[2:3])

"""
New dataframe
"""

transformed_data = pd.DataFrame(data={'Ordering': [], 
                                      'elective_max': [], 'elective_min': [], 'elective_avg': [],
                                      'conflict_max': [], 'conflict_min': [], 'conflict_avg': [],
                                      'mode_max': [], 'mode_min': [], 'mode_avg': []})

student_only = data.iloc[:,2:]


for i,order in enumerate(list(set(data['Ordering']))):
    # Indices of row
    elective_row_index = i*3 + 0
    conflict_row_index = i*3 + 1
    mode_row_index = i*3 + 2
    # Rows
    elective_row = student_only.iloc[elective_row_index]
    conflict_row = student_only.iloc[conflict_row_index]
    mode_row = student_only.iloc[mode_row_index]
    new_row = {"Ordering": data["Ordering"][elective_row_index],
               'elective_max': float(elective_row.max()), 'elective_min': float(elective_row.min()), 'elective_avg': float(elective_row.mean()),
               'conflict_max': float(conflict_row.max()), 'conflict_min': float(conflict_row.min()), 'conflict_avg': float(conflict_row.mean()),
               'mode_max': float(mode_row.max()), 'mode_min': float(mode_row.min()), 'mode_avg': float(mode_row.mean())}
    transformed_data = pd.concat([transformed_data, pd.DataFrame([new_row])], ignore_index=True)
transformed_data.to_csv("output/"+str(args.filename)+"_table6_transformed.csv", index=False)

import random as rd
import time
import copy
import itertools

# Local packages
import instance as inst
import functions as fn
from milp_model_construction import ModelObject

"""
Lexicographic solution method
"""

class LexicographicOnly:
    def __init__(self,P,number_cores,node_memory,solution=None,fixed_elements=None):
        self.P = P
        self.cores = number_cores
        self.nodemem = node_memory
        self.solution = solution
        self.fixed_elements = fixed_elements


    # Solve all possible orderings of the objectives given
    def lexicographic_solve(self,objective_list):
        results_dictionary = {}
        for ordering in itertools.permutations(objective_list):
            [objective_values,solution] = self.lexicographic_solve_ordering(list(ordering))
            ordering_name = tuple([i[0] for i in ordering])
            results_dictionary[ordering_name] = [objective_values,solution]
        return results_dictionary


    # Solve a particular ordering of objectives
    def lexicographic_solve_ordering(self,ordered_objective_list):
        objective_values = {}
        resulting_solution = None
        # Building the model
        base_model = ModelObject(self.P,
                                solution = self.solution,
                                fixed_elements = self.fixed_elements,
                                inactive_constraints = [],
                                number_cores = self.cores, 
                                node_memory = self.nodemem)
        # Looping through
        for i,objective in enumerate(ordered_objective_list):
            base_model.set_objective(objective[0],sense=objective[1])
            if(i != 0):
                objective_name = ordered_objective_list[i-1][0]
                objective_value = objective_values[objective_name]
                objective_sense = ordered_objective_list[i-1][1]
                base_model.constrain_objective(objective_name,objective_value,sense=objective_sense)
            base_model.solve_model() # THIS BIT SHOULD APPLY F AND O EVENTUALLY
            objective_values[objective[0]] = base_model.objective_value()
        # Saving final solution file for ordering
        resulting_solution = base_model.solution
        return objective_values,resulting_solution
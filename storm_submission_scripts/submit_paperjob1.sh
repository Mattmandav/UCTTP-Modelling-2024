#!/bin/bash

#SBATCH -J UCTTP_wbg-fal10
#SBATCH -c 1
#SBATCH --threads-per-core=1
#SBATCH --mem=50G
#SBATCH -o UCTTP_wbg-fal10.out
#SBATCH --mail-type=end
#SBATCH --mail-user=m.davison2@lancaster.ac.uk

source ~/start-pyenv

export OMP_NUM_THREADS=1

srun python main.py --filename 'wbg-fal10' --solvercores 1

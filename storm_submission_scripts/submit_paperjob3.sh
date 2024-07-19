#!/bin/bash

#SBATCH -J UCTTP_muni-fsps-spr17
#SBATCH -c 3
#SBATCH --threads-per-core=1
#SBATCH --mem=480G
#SBATCH -o UCTTP_muni-fsps-spr17.out
#SBATCH --mail-type=end
#SBATCH --mail-user=m.davison2@lancaster.ac.uk

source ~/start-pyenv

export OMP_NUM_THREADS=3

srun python main.py --filename 'muni-fsps-spr17' --solvercores 3 --solvernodefile 5 --studentcount 100 --studentstart 600

#!/bin/bash

#SBATCH -J UCTTP_mary-fal18
#SBATCH -c 1
#SBATCH --threads-per-core=1
#SBATCH --mem=100G
#SBATCH -o UCTTP_mary-fal18.out
#SBATCH --mail-type=end
#SBATCH --mail-user=m.davison2@lancaster.ac.uk

source ~/start-pyenv

export OMP_NUM_THREADS=1

srun python main.py --filename 'mary-fal18' --solvercores 1 --solvernodefile 1 --studentcount 300 --studentstart 600


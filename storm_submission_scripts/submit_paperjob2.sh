#!/bin/bash

#SBATCH -J UCTTP_pu-cs-fal07
#SBATCH -c 32
#SBATCH --threads-per-core=1
#SBATCH --mem=400G
#SBATCH -o UCTTP_pu-cs-fal07.out
#SBATCH --mail-type=end
#SBATCH --mail-user=m.davison2@lancaster.ac.uk

source ~/start-pyenv

export OMP_NUM_THREADS=32

srun python main.py --filename 'pu-cs-fal07' --solvercores 32 --solvernodefile 400 --studentcount 1000 --studentstart 1000


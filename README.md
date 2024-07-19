# UCTTP Modelling Paper

## Setup

You will need to set up a folder called "data", a folder called "output" and a folder called "processed_data". The reason we do not include these directories or the contents of these directories as they either include [ITC2019 data](https://www.itc2019.org/instances/all) or Lancaster University data that we do not want to distribute.

## Running the model

To run the experiments seen in [Davison et al. 2024](https://www.research.lancs.ac.uk/portal/en/publications/-(b2c9e42d-0a4f-400b-aa9d-1418f5934a32).html) then run the command corresponding to the experiment you would like to run. Change the `--solvercores` and `--solvernodefile` options to suit your hardware.

#### wbg-fal10 experiment
```cmd
py main.py --filename 'wbg-fal10' --solvercores 1
```
#### pu-cs-fal07 experiment
```cmd
py main.py --filename 'pu-cs-fal07' --solvercores 32 --solvernodefile 400 --studentcount 1000 --studentstart 1000
```
#### muni-fsps-spr17 experiment
```cmd
py main.py --filename 'muni-fsps-spr17' --solvercores 3 --solvernodefile 5 --studentcount 100 --studentstart 600
```
#### mary-fal18 experiment
```cmd
py main.py --filename 'mary-fal18' --solvercores 1 --solvernodefile 1 --studentcount 300 --studentstart 600
```

## Reproducing Table 6

The results that are in the output folder have a file named `<filename>_table6.csv` however the data included is disaggregated student data rather than statistics. To produce the values seen in Table 6 run the following command:
```cmd
py output_reading.py --filename <filename>
```
This will produce a file called `<filename>_transformed.csv`.

## Reproducing mary-fal18 plots

After running the model for mary-fal18 using the above command, then the plots (Figures 2 and 3) can be recreated by running the R file `plotting.R`.

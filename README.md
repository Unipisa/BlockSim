## What is BlockSim Simulation Framework?

BlockSim simulation framework is an open source blockchain simulator developed by Maher Alharby and Aad van Moorsel:

https://github.com/maher243/BlockSim

In February 2022, the existing BlockSim model of the Bitcoin protocol has been significantly improved by University of Pisa, Dept. of Ingegneria dell'Informazione.

## Additional/Improved BlockSim Bitcoin Protocol Features
- At consensus layer, we introduce Segregated Witness ( https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki, https://github.com/bitcoin/bips/blob/master/bip-0144.mediawiki );
- At netwok layer, we update the simulated block propagation process. Block delay is now estimated via linear regression (almost two years of real-world Bitcoin block size and block delay data, from January 1st, 2020 to November 30th, 2021) on a per-simulated-block basis;
- Up-to-date parametrization of input parameters (reflecting the state of the Bitcoin blockchain in November 2021);
- Introducing a new performance evaluation metric: "Total reward per block", i.e., the sum of the static block reward and transaction fees per block (in BTC/block)

## Installation and Requirements

Before you can use BlockSim simulator, you need to have **Python version 3 or above** installed in your machine as well as the following packages installed:

- pandas
>pip3 install pandas
- numpy 
>pip3 install numpy
- sklearn 
>pip3 install sklearn
- xlsxwriter
>pip3 install xlsxwriter
- scipy
>pip3 install scipy
- metalog
>pip3 install metalog

## Running the simulator

Before you run the simulator, you can access the configuration file *InputsConfig.py* to choose the model of interest (Base Model 0, Bitcoin Model 1 and Ethereum Model 2) and to set up the related parameters.

To run the simulator, one needs to trigger the main class *Main.py* from the command line:
> python3 Main.py

## Statistics and Results

The results of the simulator is printed in an excel file at the end of the simulation.

## License

SimBlock is licensed under the Apache License, Version2.0.

## Contact

E-mail: mariano.basile@ing.unipi.it

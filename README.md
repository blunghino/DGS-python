 dgs_wav.py (serial version)
 dgs_wav_p.py (parallel version)

Python software to calculate the grain size distribution from an image of sediment or other granular material

To run the program, download and unzip, open a terminal or your Python development environment (e.g. IDLE, Spyder), cd to the DGS-master directory, then execute the program (for example in the command window type):

EXAMPLE:
python dgs_wav.py -f /my/sediment/images/directory

Note that the larger the density parameter, the longer the execution time. If a large density is required, please use the parallelised version of this code, dgs_wav_p.py which uses the joblib library. It should speed things up 10x or more if you have a number of processors 

EXAMPLE:
python dgs_wav_p.py -f /my/sediment/images/directory -n 8

This program implements the algorithm of 
Buscombe, D. (2013, in press) Transferable Wavelet Method for Grain-Size Distribution from Images of Sediment Surfaces and Thin Sections, and Other Natural Granular Patterns, Sedimentology
 
Written by Daniel Buscombe, various times in 2012 and 2013
while at
School of Marine Science and Engineering, University of Plymouth, UK
and now:
Grand Canyon Monitoring and Research Center, U.G. Geological Survey, Flagstaff, AZ 

Please contact:
dbuscombe@usgs.gov

to report bugs and discuss the code, algorithm, collaborations

For the latest code version please visit:
https://github.com/dbuscombe-usgs

See also the project blog: 
http://dbuscombe-usgs.github.com/

Please download, try, report bugs, fork, modify, evaluate, discuss. Thanks for stopping by!

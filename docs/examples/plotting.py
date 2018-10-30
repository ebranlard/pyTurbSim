"""
This script provides an example usage of the TurbGen API.
"""

# Begin by importing the TurbGen API and plotting tools
### BLOCK1
import pyts.api as pyts
import pyts.plot.api as plt
from matplotlib.pylab import show
### BLOCK1.END
# Define some variables for the TurbGen run:
### BLOCK2
refht = 4
ustar = 0.03
Uref = 3.

# This creates a TurbGen 'run object':
tsr = pyts.tsrun()

tsr.grid = pyts.tsGrid(center=refht,
                       ny=3,
                       nz=5,
                       height=5,
                       width=5,
                       time_sec=3000,
                       dt=0.5,)
### BLOCK2.END

tsr.prof = pyts.profModels.h2l(Uref, refht, ustar)
tsr.spec = pyts.specModels.tidal(ustar, refht)
tsr.cohere = pyts.cohereModels.nwtc()
tsr.stress = pyts.stressModels.tidal(ustar, refht)

# Run TurbGen:
out = tsr()

# Create a 'TurbGen plotting figure' (plotting object):
fig = plt.summfig()

# Now just call this plotting object's 'plot' method with the
# TurbGen output as input:
fig.plot(out, color='k')

# These plotting objects are smart; when the same 'plot' method
# is given a TurbGen 'run' object it plots the target values:
fig.plot(tsr, color='r', linestyle='--')

fig.finalize()

show()

# dgs_wav_p.py
# wavelet-based digital grain size analysis (parallelised)
# Written by Daniel Buscombe, various times in 2012 and 2013
# while at
# School of Marine Science and Engineering, University of Plymouth, UK
# then
# Grand Canyon Monitoring and Research Center, U.G. Geological Survey, Flagstaff, AZ 
# please contact:
# dbuscombe@usgs.gov
# for lastest code version please visit:
# https://github.com/dbuscombe-usgs
# see also (project blog):
# http://dbuscombe-usgs.github.com/
#====================================
#   This function is part of 'dgs_wav.py' software
#   This software is in the public domain because it contains materials that originally came 
#   from the United States Geological Survey, an agency of the United States Department of Interior. 
#   For more information, see the official USGS copyright policy at 
#   http://www.usgs.gov/visual-id/credit_usgs.html#copyright
#====================================
'''
 DGS_WAVE_||.PY
 {D}IGITAL {G}RAIN {S}IZE - {WAV}ELET _ {||} (parallel)
 Python function to compute estimates of grain size distribution 
 using the continuous wavelet transform method of Buscombe (2013)
 from an image of sediment where grains are clearly resolved
 DOES NOT REQUIRE CALIBRATION

 REQUIRED INPUTS:
 folder e.g. '/home/my_sediment_images'
 if 'pwd', then the present directory is analysed

 OPTIONAL INPUTS [default values]
 density = process every density lines of image [100]
 doplot = 0=no, 1=yes [0]
 resolution = spatial resolution of image in mm/pixel [1]

 inputs must be separated by a space 

 OUTPUTS:
 1) a text file which contains summary measures, including arithmetic mean grain size and standard deviation
 2) a text file containing the particle size distribution (column 1= sizes and column 2= associated densities)

 EXAMPLES:

 1) process present working directory using defaults
 python dgs_wav_p.py -f pwd 

 2) process a folder somewhere on the computer
 python dgs_wav_p.py -f /home/my_sediment_images

 3) process a folder with a sample density of 50
 python dgs_wav_p.py -f /home/my_sediment_images -d 50 

 4) process a folder with a sample density of 100, and do a plot for each image 
 python dgs_wav_p.py -f /home/my_sediment_images -d 50 -p 1

 5) process a folder with a sample density of 100, don't do a plot for each image, and use mm/pixel resolution 0.05 
 python dgs_wav_p.py -f /home/my_sediment_images -d 50 -p 1 -r 0.05


 SOFTWARE REQUIREMENTS:
 1) Python (developed/tested using Python 2.7)
 2) Numpy  (developed/tested using numpy.version.version > 1.6.2)
 3) Pylab  (developed/tested using the version which came with matplotlib.__version__ > 1.0.1)
 4) Scipy  (developed/tested using scipy.version.version > 0.9.0)
 5) PIL    (Python Imaging Library, developed/tested using Image.VERSION > 1.1.7)
 5) joblib (Lightweight piping library, https://pypi.python.org/pypi/joblib, developed/tested using joblib.__version__ = 0.6.4)

 Author:  Daniel Buscombe
           Grand Canyon Monitoring and Research Center
           United States Geological Survey
           Flagstaff, AZ 86001
           dbuscombe@usgs.gov
 Version: 1.0      Revision: October, 2013
 First Revision of dgs_wav.py: January 18 2013   
 First Revision of dgs_wav_p.py: October 8 2013   

'''

import numpy as np
import pylab as mpl
import sys, getopt, os, glob, Image, time
import scipy.signal as sp
from joblib import Parallel, delayed

################################################################
############## SUBFUNCTIONS ####################################
################################################################

def column(matrix, i):
    """
    return a column from a matrix
    """
    return [row[i] for row in matrix]

################################################################
def sgolay2d ( z, window_size, order, derivative=None):
    """
    do 2d filtering on matrix
    from http://www.scipy.org/Cookbook/SavitzkyGolay
    """
    # number of terms in the polynomial expression
    n_terms = ( order + 1 ) * ( order + 2)  / 2.0

    if  window_size % 2 == 0:
        raise ValueError('window_size must be odd')

    if window_size**2 < n_terms:
        raise ValueError('order is too high for the window size')

    half_size = window_size // 2

    # exponents of the polynomial. 
    # p(x,y) = a0 + a1*x + a2*y + a3*x^2 + a4*y^2 + a5*x*y + ... 
    # this line gives a list of two item tuple. Each tuple contains 
    # the exponents of the k-th term. First element of tuple is for x
    # second element for y.
    # Ex. exps = [(0,0), (1,0), (0,1), (2,0), (1,1), (0,2), ...]
    exps = [ (k-n, n) for k in range(order+1) for n in range(k+1) ]

    # coordinates of points
    ind = np.arange(-half_size, half_size+1, dtype=np.float64)
    dx = np.repeat( ind, window_size )
    dy = np.tile( ind, [window_size, 1]).reshape(window_size**2, )

    # build matrix of system of equation
    A = np.empty( (window_size**2, len(exps)) )
    for i, exp in enumerate( exps ):
        A[:,i] = (dx**exp[0]) * (dy**exp[1])

    # pad input array with appropriate values at the four borders
    new_shape = z.shape[0] + 2*half_size, z.shape[1] + 2*half_size
    Z = np.zeros( (new_shape) )
    # top band
    band = z[0, :]
    Z[:half_size, half_size:-half_size] =  band -  np.abs( np.flipud( z[1:half_size+1, :] ) - band )
    # bottom band
    band = z[-1, :]
    Z[-half_size:, half_size:-half_size] = band  + np.abs( np.flipud( z[-half_size-1:-1, :] )  -band )
    # left band
    band = np.tile( z[:,0].reshape(-1,1), [1,half_size])
    Z[half_size:-half_size, :half_size] = band - np.abs( np.fliplr( z[:, 1:half_size+1] ) - band )
    # right band
    band = np.tile( z[:,-1].reshape(-1,1), [1,half_size] )
    Z[half_size:-half_size, -half_size:] =  band + np.abs( np.fliplr( z[:, -half_size-1:-1] ) - band )
    # central band
    Z[half_size:-half_size, half_size:-half_size] = z

    # top left corner
    band = z[0,0]
    Z[:half_size,:half_size] = band - np.abs( np.flipud(np.fliplr(z[1:half_size+1,1:half_size+1]) ) - band )
    # bottom right corner
    band = z[-1,-1]
    Z[-half_size:,-half_size:] = band + np.abs( np.flipud(np.fliplr(z[-half_size-1:-1,-half_size-1:-1]) ) - band )

    # top right corner
    band = Z[half_size,-half_size:]
    Z[:half_size,-half_size:] = band - np.abs( np.flipud(Z[half_size+1:2*half_size+1,-half_size:]) - band )
    # bottom left corner
    band = Z[-half_size:,half_size].reshape(-1,1)
    Z[-half_size:,:half_size] = band - np.abs( np.fliplr(Z[-half_size:, half_size+1:2*half_size+1]) - band )

    # solve system and convolve
    if derivative == None:
        m = np.linalg.pinv(A)[0].reshape((window_size, -1))
        Z = Z.astype('f')
        m = m.astype('f')
        return sp.fftconvolve(Z, m, mode='valid')
    elif derivative == 'col':
        A = A.astype('f')
        c = np.linalg.pinv(A)[1].reshape((window_size, -1))
        Z = Z.astype('f')
        return sp.fftconvolve(Z, -c, mode='valid')
    elif derivative == 'row':
        A = A.astype('f')
        Z = Z.astype('f')
        r = np.linalg.pinv(A)[2].reshape((window_size, -1))
        return sp.fftconvolve(Z, -r, mode='valid')
    elif derivative == 'both':
        A = A.astype('f')
        Z = Z.astype('f')
        c = np.linalg.pinv(A)[1].reshape((window_size, -1))
        r = np.linalg.pinv(A)[2].reshape((window_size, -1))
        return sp.fftconvolve(Z, -r, mode='valid'), sp.fftconvolve(Z, -c, mode='valid')

################################################################
def iseven(n):
   """Return true if n is even."""
   return n%2==0

################################################################
def isodd(n):
   """Return true if n is odd."""   
   return not iseven(n)

################################################################
def rescale(dat,mn,mx):
    """
    rescales an input dat between mn and mx
    """
    m = min(dat.flatten())
    M = max(dat.flatten())
    return (mx-mn)*(dat-m)/(M-m)+mn

################################################################
def pad2nxtpow2(A,ny):
    """
    zero pad numpy array up to next power 2
    """
    base2 = np.fix(np.log(ny)/np.log(2) + 0.4999)
    Y = np.zeros((1,ny+(2**(base2+1)-ny)))
    np.put(Y, np.arange(ny), A)
    return np.squeeze(Y)

################################################################
def cropcentral(im):
    """
    crop image to central box
    """
    size = min(im.size)
    originX = im.size[0] / 2 - size / 2
    originY = im.size[1] / 2 - size / 2
    cropBox = (originX, originY, originX + size, originY + size)
    return im.crop(cropBox) 

################################################################
def log2(x):
     """
     utility function to return (integer) log2
     """
     return int( np.log(float(x))/ np.log(2.0)+0.0001 )

################################################################
class Cwt:
    """
    Base class for continuous wavelet transforms
    Implements cwt via the Fourier transform
    Used by subclass which provides the method wf(self,s_omega)
    wf is the Fourier transform of the wavelet function.
    Returns an instance.
    """

    fourierwl=1.00

################################################################
    def _log2(self, x):
        # utility function to return (integer) log2
        return int( np.log(float(x))/ np.log(2.0)+0.0001 )

################################################################
    def __init__(self, data, largestscale=1, notes=0, order=2, scaling='linear'):
        """
        Continuous wavelet transform of data

        data:    data in array to transform, length must be power of 2
        notes:   number of scale intervals per octave
        largestscale: largest scale as inverse fraction of length
                 of data array
                 scale = len(data)/largestscale
                 smallest scale should be >= 2 for meaningful data
        order:   Order of wavelet basis function for some families
        scaling: Linear or log
        """
        ndata = len(data)
        self.order = order
        self.scale = largestscale
        self._setscales(ndata,largestscale,notes,scaling)
        self.cwt = np.zeros((self.nscale,ndata), np.complex64)
        omega = np.array(range(0,ndata/2)+range(-ndata/2,0))*(2.0*np.pi/ndata)
        datahat = np.fft.fft(data)
        self.fftdata = datahat
        #self.psihat0=self.wf(omega*self.scales[3*self.nscale/4])
        # loop over scales and compute wvelet coeffiecients at each scale
        # using the fft to do the convolution
        for scaleindex in range(self.nscale):
            currentscale = self.scales[scaleindex]
            self.currentscale = currentscale  # for internal use
            s_omega = omega*currentscale
            psihat = self.wf(s_omega)
            psihat = psihat *  np.sqrt(2.0*np.pi*currentscale)
            convhat = psihat * datahat
            W    = np.fft.ifft(convhat)
            self.cwt[scaleindex,0:ndata] = W 
        return

################################################################    
    def _setscales(self,ndata,largestscale,notes,scaling):
        """
        if notes non-zero, returns a log scale based on notes per ocave
        else a linear scale
        notes!=0 case so smallest scale at [0]
        """
        if scaling=="log":
            if notes<=0: notes=1 
            # adjust nscale so smallest scale is 2 
            noctave = self._log2( ndata/largestscale/2 )
            self.nscale = notes*noctave
            self.scales = np.zeros(self.nscale,float)
            for j in range(self.nscale):
                self.scales[j] = ndata/(self.scale*(2.0**(float(self.nscale-1-j)/notes)))
        elif scaling=="linear":
            nmax = ndata/largestscale/2
            self.scales = np.arange(float(2),float(nmax))
            self.nscale = len(self.scales)
        else: raise ValueError, "scaling must be linear or log"
        return
 
################################################################   
    def getdata(self):
        """
        returns wavelet coefficient array
        """
        return self.cwt

################################################################
    def getcoefficients(self):
        return self.cwt

################################################################
    def getpower(self):
        """
        returns square of wavelet coefficient array
        """
        return (self.cwt* np.conjugate(self.cwt)).real

################################################################
    def getscales(self):
        """
        returns array containing scales used in transform
        """
        return self.scales

################################################################
    def getnscale(self):
        """
        return number of scales
        """
        return self.nscale

################################################################
# wavelet classes    
class Morlet(Cwt):
    """
    Morlet wavelet
    """
    _omega0 = 6.0 #5.0
    fourierwl = 4* np.pi/(_omega0+ np.sqrt(2.0+_omega0**2))

################################################################
    def wf(self, s_omega):
        H = np.ones(len(s_omega))
        n = len(s_omega)
        for i in range(len(s_omega)):
            if s_omega[i] < 0.0: H[i] = 0.0
        # !!!! note : was s_omega/8 before 17/6/03
        xhat = 0.75112554*( np.exp(-(s_omega-self._omega0)**2/2.0))*H
        return xhat

################################################################
def processimage( item, density, doplot, resolution, folder, numproc ):
    """
    main processing program which reads image and calculates grain size distribution
    """
    try:
        im = Image.open(item).convert("L")
    except IOError:
        print 'cannot open', item
        sys.exit(2)

    # crop a square box from centre of image
    region = cropcentral(im)

    # convert to numpy array
    region = np.array(region)
    nx, ny = np.shape(region)

    # resize image so it is half the size (to reduce computational time)
    #useregion= np.array(imresize(region,(( nx/2, ny/2 )))).T
    #nx, ny = np.shape(useregion)
    mn = min(nx,ny)

    mult = 6*int(float(100*(1/np.std(region.flatten()))))

    try:
        if isodd(mn/4):
             window_size = (mn/4)
        else:
             window_size = (mn/4)-1
        Zf = sgolay2d( region, window_size, order=3)

        # rescale filtered image to full 8-bit range
        useregion = rescale(region-Zf,0,255)

    except:
        print "flattening failed"
        useregion = region

    wavelet = Morlet
    maxscale = 3
    notes = 8 # suboctaves per octave
    #scaling = "log" #or "linear"
    scaling = "log"

    # for smoothing:
    l2nx = np.ceil( np.log(float(ny))/ np.log(2.0)+0.0001 )
    npad = int(2**l2nx)
    k = np.r_[0.:np.fix(npad)/2]
    k = k*((2.*np.pi)/npad)
    kr = -k[::-1]
    kr = kr[:np.asarray(np.fix((npad-1)/2), dtype=np.int)]
    k2 = np.hstack((0,k,kr))**2

    # each row is treated using a separate queued job
    print 'analysing every ',density,' rows of a ',nx,' row image'
    d = Parallel(n_jobs = numproc, verbose=10)(delayed(parallel_me)(column(np.asarray(useregion), k), ny, wavelet, maxscale, notes, scaling, k2, npad) for k in range(1,nx-1,density))

    A = column(np.asarray(useregion), 1)
    # detrend the data
    A = sp.detrend(A)
    # pad detrended series to next power 2 
    Y = pad2nxtpow2(A,ny)
    # Wavelet transform the data
    cw = wavelet(Y,maxscale,notes,scaling=scaling)     
    cwt = cw.getdata()
    # get rid of padding before returning
    cwt = cwt[:,0:ny] 
    scales = cw.getscales()    
    del A, Y, cw, cwt

    Or1 = np.reshape(d, (-1,np.squeeze(np.shape(scales)))).T
    # column-wise variance, scaled
    varcwt1 = np.var(Or1,axis=1) 
    varcwt1 = varcwt1/np.sum(varcwt1)
    
    svarcwt = varcwt1*sp.kaiser(len(varcwt1),mult)
    svarcwt = svarcwt/np.sum(svarcwt)
    
    index = np.nonzero(scales<ny/3)
    scales = scales[index]
    svarcwt = svarcwt[index]
    scales = scales*1.5

    # get real scales by multiplying by resolution (mm/pixel)
    scales = scales*resolution

    mnsz = np.sum(svarcwt*scales)
    print "mean size = ", mnsz 

    srt = np.sqrt(np.sum(svarcwt*((scales-mnsz)**2)))
    print "stdev = ",srt 

    sk = (sum(svarcwt*((scales-mnsz)**3)))/(100*srt**3)
    print "skewness = ",sk

    kurt = (sum(svarcwt*((scales-mnsz)**4)))/(100*srt**4)
    print "kurtosis = ",kurt

    if doplot:
       fig = mpl.figure(1)
       mpl.subplot(221)
       Mim = mpl.imshow(im,cmap=mpl.cm.gray)

       mpl.subplot(222)
       Mim = mpl.imshow(region,cmap=mpl.cm.gray)

       showim = Image.fromarray(np.uint8(region))
       size = min(showim.size)
       originX = np.round(showim.size[0] / 2 - size / 2)
       originY = np.round(showim.size[1] / 2 - size / 2)
       cropBox = (originX, originY, originX + np.asarray(mnsz*5,dtype='int'), originY + np.asarray(mnsz*5,dtype='int'))
       showim = showim.crop(cropBox)

       mpl.subplot(223)
       Mim = mpl.imshow(showim,cmap=mpl.cm.gray)

       mpl.subplot(224)
       mpl.ylabel('Power')
       mpl.xlabel('Period')
#       mpl.plot(scales,varcwt1)
#       mpl.hold(True)
       mpl.plot(scales,svarcwt,'g-')

       (dirName, fileName) = os.path.split(item)
       (fileBaseName, fileExtension)=os.path.splitext(fileName)

       mpl.savefig(folder+os.sep+"outputs"+os.sep+fileBaseName+'_res.png')
       mpl.close()
#       mpl.show()

    return scales, svarcwt, mnsz, srt, sk, kurt

################################################################
def writeout( item, sz, pdf, mnsz, srt, sk, kurt, resolution ):
    """
    writes results to file
    """

    with open(item+'_psd.txt', 'w') as f:
     np.savetxt(f, np.hstack((ascol(sz),ascol(pdf))), delimiter=', ', fmt='%s')   
    print 'psd results saved to ',item,'_psd.txt'

    title = item+ "_summary.txt"
    fout = open(title,"w")

    fout.write("%"+time.strftime('%l:%M%p %z on %b %d, %Y')+"\n") 

    fout.write("% grain size results ..."+"\n")
    fout.write("% resolution:\n")
    fout.write(str(resolution)+"\n")
    fout.write('% mean grain size:'+"\n")
    fout.write(str(mnsz)+"\n")
    fout.write('% sorting :'+"\n")
    fout.write(str(srt)+"\n")
    fout.write('% skewness :'+"\n")
    fout.write(str(sk)+"\n")
    fout.write('% kurtosis :'+"\n")
    fout.write(str(kurt)+"\n")

    fout.close()
    print 'summary results saved to ',title

################################################################
def ascol( arr ):
    '''
    reshapes row matrix to be a column matrix (N,1).
    '''
    if len( arr.shape ) == 1: arr = arr.reshape( ( arr.shape[0], 1 ) )
    return arr

################################################################
def parallel_me(A, ny, wavelet, maxscale, notes, scaling, k2, npad):
   # extract column from image
#   A = column(np.asarray(useregion), k)
   # detrend the data
   A = sp.detrend(A)
   # pad detrended series to next power 2 
   Y = pad2nxtpow2(A,ny)
   # Wavelet transform the data
   cw = wavelet(Y,maxscale,notes,scaling=scaling)     
   cwt = cw.getdata()
   # get rid of padding before returning
   cwt = cwt[:,0:ny] 
   scales = cw.getscales()
   # get scaled power spectrum
   wave = np.tile(1/scales, (ny,1)).T*(np.absolute(cwt)**2)

   # smooth
   twave = np.zeros(np.shape(wave)) 
   snorm = scales/1.
   for ii in range(0,np.shape(wave)[0]):
       F = np.exp(-.5*(snorm[ii]**2)*k2)
       smooth = np.fft.ifft(np.squeeze(F)*np.squeeze(np.fft.fft(wave[ii,:],npad)))
       twave[ii,:] = smooth[:ny].real

   # store the variance of real part of the spectrum
   dat = np.var(twave,axis=1)
   dat = dat/sum(dat)
   return np.squeeze(dat.T) #O1


################################################################
############## MAIN PROGRAM ####################################
################################################################

# start timer
if os.name=='posix': # true if linux/mac or cygwin on windows
    start = time.time()
    os.system('clear') # on linux 
else: # windows
    start = time.clock()
    os.system('cls') #on windows

print "==========================================="
print "======DIGITAL GRAIN SIZE: WAVELET=========="
print "==========================================="
print "=CALCULATE GRAIN SIZE-DISTRIBUTION FROM AN="
print "====IMAGE OF SEDIMENT/GRANULAR MATERIAL===="
print "==========================================="
print "======A PROGRAM BY DANIEL BUSCOMBE========="
print "========USGS, FLAGSTAFF, ARIZONA==========="
print "=========REVISION 2.0, OCT 2013============"
print "==========================================="

# get list of input arguments and pre-allocate arrays
argv = sys.argv[1:]
folder = ''; density = ''
doplot = ''; resolution = ''
numproc = ''

# parse inputs to variables
try:
   opts, args = getopt.getopt(argv,"hf:d:p:r:n:")
except getopt.GetoptError:
     print 'dgs_wav.py -f <folder> [[-d <density> -p < doplot (0=no, 1=yes)> -r <resolution (mm/pixel)> -n <number of processors> ]]'
     sys.exit(2)
for opt, arg in opts:
   if opt == '-h':
      print 'dgs_wav.py -f <folder> [[-d <density> -p < doplot (0=no, 1=yes)> -r <resolution (mm/pixel)> -n <number of processors> ]]'
      sys.exit()
   elif opt in ("-f"):
      folder = arg
   elif opt in ("-d"):
      density = arg
   elif opt in ("-p"):
      doplot = arg
   elif opt in ("-r"):
      resolution = arg
   elif opt in ("-n"):
      numproc = arg

# exit program if no input folder given
if not folder:
   print 'A folder is required!!!!!!'
   sys.exit(2)

# print given arguments to screen and convert data type where necessary
if folder:
   print 'Input folder is ', folder
if density:
   density = np.asarray(density,int)
   print 'Every '+str(density)+' rows will be processed'
if doplot:
   doplot = np.asarray(doplot,int)
   print 'Doplot is '+str(doplot)
if resolution:
   resolution = np.asarray(resolution,float)
   print 'Resolution is '+str(resolution)
if numproc:
   numproc = np.asarray(numproc,int)
   print 'Number of processors is '+str(numproc)

if not density:
   density = 10
   print '[Default] Density is '+str(density)

if not doplot:
   doplot = 0
   print '[Default] No plot will be produced. To change this, set doplot to 1'

if not resolution:
   resolution = 1
   print '[Default] Resolution is '+str(resolution)+' mm/pixel'

if not numproc:
   numproc = 4
   print '[Default] Number of processors is '+str(numproc)

# special case = pwd
if folder=='pwd':
   folder = os.getcwd()

# if make plot
if doplot:
   # if directory does not exist
   if os.path.isdir(folder+os.sep+"outputs")==False:
      # create it
      os.mkdir(folder+os.sep+"outputs")

# cover all major file types
files1 = glob.glob(folder+os.sep+"*.JPG")
files2 = glob.glob(folder+os.sep+"*.jpg")
files3 = glob.glob(folder+os.sep+"*.jpeg")
files4 = glob.glob(folder+os.sep+"*.TIF")
files5 = glob.glob(folder+os.sep+"*.tif")
files6 = glob.glob(folder+os.sep+"*.TIFF")
files7 = glob.glob(folder+os.sep+"*.tiff")
files8 = glob.glob(folder+os.sep+"*.PNG")
files9 = glob.glob(folder+os.sep+"*.png")

# initiate counter for counting how many images there are
count=0

if files1:
   for item in files1:
        print "==========================================="
        print "Analysing "+item
        sz, pdf, mnsz, srt, sk, kurt = processimage( item, density, doplot, resolution, folder, numproc )
        writeout( item, sz, pdf, mnsz, srt, sk, kurt, resolution )
        count = count+1
if files2:
   for item in files2:
        print "==========================================="
        print "Analysing "+item
        sz, pdf, mnsz, srt, sk, kurt = processimage( item, density, doplot, resolution, folder, numproc )
        writeout( item, sz, pdf, mnsz, srt, sk, kurt, resolution )
        count = count+1
if files3:
   for item in files3:
        print "==========================================="
        print "Analysing "+item
        sz, pdf, mnsz, srt, sk, kurt = processimage( item, density, doplot, resolution, folder, numproc )
        writeout( item, sz, pdf, mnsz, srt, sk, kurt, resolution )
        count = count+1
if files4:
   for item in files4:
        print "==========================================="
        print "Analysing "+item
        sz, pdf, mnsz, srt, sk, kurt = processimage( item, density, doplot, resolution, folder, numproc )
        writeout( item, sz, pdf, mnsz, srt, sk, kurt, resolution )
        count = count+1
if files5:
   for item in files5:
        print "==========================================="
        print "Analysing "+item
        sz, pdf, mnsz, srt, sk, kurt = processimage( item, density, doplot, resolution, folder, numproc )
        writeout( item, sz, pdf, mnsz, srt, sk, kurt, resolution )
        count = count+1
if files6:
   for item in files6:
        print "==========================================="
        print "Analysing "+item
        sz, pdf, mnsz, srt, sk, kurt = processimage( item, density, doplot, resolution, folder, numproc )
        writeout( item, sz, pdf, mnsz, srt, sk, kurt, resolution )
        count = count+1
if files7:
   for item in files7:
        print "==========================================="
        print "Analysing "+item
        sz, pdf, mnsz, srt, sk, kurt = processimage( item, density, doplot, resolution, folder, numproc )
        writeout( item, sz, pdf, mnsz, srt, sk, kurt, resolution )
        count = count+1
if files8:
   for item in files8:
        print "==========================================="
        print "Analysing "+item
        sz, pdf, mnsz, srt, sk, kurt = processimage( item, density, doplot, resolution, folder, numproc )
        writeout( item, sz, pdf, mnsz, srt, sk, kurt, resolution )
        count = count+1
if files9:
   for item in files9:
        print "==========================================="
        print "Analysing "+item
        sz, pdf, mnsz, srt, sk, kurt = processimage( item, density, doplot, resolution, folder, numproc )
        writeout( item, sz, pdf, mnsz, srt, sk, kurt, resolution )
        count = count+1

print "==========================================="
if os.name=='posix': # true if linux/mac
    elapsed = (time.time() - start)
else: # windows
    elapsed = (time.clock() - start)
print "Processing took ", elapsed , "seconds to analyse ", count, "images"

################################################################
############## END OF MAIN PROGRAM #############################
################################################################



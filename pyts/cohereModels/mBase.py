"""
This is the base module for coherence models.

function of frequency.  That is
Coherence is defined as
"""
try:
    from ..base import gridProps,modelBase,np,ts_float,tslib,dbg
except ValueError:
    from base import gridProps,modelBase,np,ts_float,tslib,dbg


class cohereCalc(gridProps):
    """
    A cross-spectral matrix 'calculator' object.

    This is a memory-efficient representation of the full cross-spectral matrix.
    The 'full' cross-spectral matrix size is large: (3 x n_p x n_p x n_f).

    This 'calculator' object saves memory by taking advantage of the fact that each
    component (first dimension of full array) are utilized independently by TurbSim.
    Therefore, this cohereCalc class utilizes 1/3 the space in memory
    (i.e. n_p x n_p x n_f), and calculates the cross-spectral matrix for each
    component as-needed.

    See also
    --------
    cohereCalc_pack - A more memory efficient form of the cross-spectral calculator
                      utilized when 'tslib' is available.
    
    """
    _crossSpec_name=None

    @property
    def _i_diag(self,):
        """
        The diagonal indices of this coherence calculator.
        """
        return 2*[np.arange(self.grid.n_p)]

    def __getitem__(self,comp):
        if hasattr(comp,'__len__'):
            self.__call__(comp[0])
            return self._crossSpec[comp[1:]]
        return self.__call__(comp)

    def __setitem__(self,ind,val):
        if hasattr(ind,'__len__'):
            if len(ind)==2:
                i2=(ind[0],slice(None),ind[1])
            elif len(ind)==3:
                i2=(ind[0],ind[2],ind[1])
            elif len(ind)>3:
                i2=(ind[0],ind[2],ind[1],ind[3:])
            self._crossSpec[i2]=val
        self._crossSpec[ind]=val # !!!FIXTHIS, I don't believe the cross-spectral matrix is currently mirrored!

    def __init__(self,tsrun):
        self._crossSpec=np.empty((tsrun.grid.n_p,tsrun.grid.n_p,tsrun.grid.n_f),dtype=ts_float,order='F') # This is a working array used 1-component at a time.
        self.grid=tsrun.grid
        self.spec=tsrun.spec
        self.prof=tsrun.prof
        self.ncore=tsrun.ncore # Number of CPU cores (for use with tslib)

    @property
    def _iter_flat_inds(self,):
        for jj in range(self.n_p):
            for ii in range(jj,self.n_p):
                yield (ii,jj),(ii,jj) # This is correct, we need to return

    def __call__(self,comp):
        """
        Calculate the cross-spectral matrix, Sij for velocity component *comp* (0,1,2).
        
        This function sets and returns the variable self._crossSpec for the component *comp* (i.e. u,v,w).
        """
        if self._crossSpec_name==comp:
            return self._crossSpec
        self.model.calc(self,comp)
        self._crossSpec_name=comp
        return self._crossSpec

    def __iter__(self,):
        """
        Iterate over the u,v,w components of the spectrum.

        Yields cross-spectral matrix.
        """
        for comp in self.grid.comp:
            yield self(comp)

class cohereCalc_pack(cohereCalc):
    """
    A cross-spectral matrix 'calculator' object.

    This is a memory-efficient representation of the full cross-spectral matrix.
    The 'full' cross-spectral matrix size is large: (3 x n_p x n_p x n_f).

    This 'calculator' object saves memory by taking advantage of two factors:
      1) Each component (first dimension of full array) is utilized independently
         by TurbSim.
      2) Each component of the cross-spectral matrix is symmetric.
    By computing the cross-spectral matrix on-demand, we can reduce the memory
    demands by 1/3, and by taking advantage of the symmetry can further reduce
    memory demands by nearly 1/2.  Thus, this format utilizes nearly 1/6 the memory
    as the 'full' cross-spectral matrix.

    See also
    --------
    cohereCalc - A less memory efficient form of this cross-spectral calculator
                 utilized when 'tslib' is not available.
    
    """

    @property
    def _i_diag(self,):
        """
        The diagonal indices of this coherence calculator.
        """
        return np.cumsum(np.arange(self.grid.n_p,0,-1)+1)-self.grid.n_p-1

    @property
    def _iter_flat_inds(self,):
        indx=0
         # The _crossSpec_pack needs to be in column order for lapack's SPPTRF.
        for jj in range(self.n_p):
            for ii in range(jj,self.n_p):
                yield (ii,jj),indx
                indx+=1

    def __init__(self,tsrun):
        self._crossSpec=np.empty((tsrun.grid.n_p*(tsrun.grid.n_p+1)/2,tsrun.grid.n_f),dtype=ts_float,order='F') # This is a working array, used 1-component at a time.
        self.grid=tsrun.grid
        self.spec=tsrun.spec
        self.prof=tsrun.prof
        self.ncore=tsrun.ncore # Number of CPU cores (for use with tslib)

class cohModelBase(modelBase):
    """
    Examples
    --------
    When a coherence model class is called, it returns a 'coherence model instance'
    (as expected) e.g.:
    cm = myCohereModel(inarg1,inarg2,...)

    A 'coherence model instance' is an instance of a specific coherence model that is
    independent of a turbsim run (i.e. the coherence model instance holds parameters
    that are specific the grid, mean profile model, or spectral model.
    
    When a 'coherence model instance' is called, it returns a 'coherence instance',
    e.g.:
    coh=cm(tsr)

    Where tsr is a 'tsrun' object.
    
    """
    lib=None # This must be set explicitly in a subclass that utilizes it

    def __call__(self,tsrun):
        """
        Calculate the coherence matrix for TurbSim run *tsrun* according to this
        coherence model. The grid, profile and spectrum (tsrun.grid, tsrun.prof,
        tsrun.spec) must already be defined for the tsrun.

        Parameters
        ----------
        tsrun : A 'TurbSim run' object that contains the grid, prof and spec
                attributes.

        Returns
        -------
        A coherence instance (array or 'calculator'), e.g.:
        cohi=thisCohereModel(tsrun)

        The coherence instance is either an array of the full
        cross-spectral matrix (3 x n_p x n_p x n_f), or a 'calculator' that returns
        the components of that array. Either way, the components of the cross-spectral
        matrix (csm) can be obtained from:
        
        csm_u=cohi[0]
        csm_v=cohi[1]
        csm_w=cohi[2]

        """
        #out=np.empty((self.n_comp,self.n_p,self.n_f+1),dtype=ts_float,order='F')
        if tslib is None:
            out=cohereCalc(tsrun)
        else:
            out=cohereCalc_pack(tsrun)
        out.model=self
        if hasattr(self,'init_cohi'):
            self.init_cohi(out)
        #tsrun.cohere=out
        return out
    
    def calc(self,cohi,comp):
        """
        Compute and set the full cross-spectral matrix for component
        *comp* for 'coherence calculator' instance *cohi*.

        This method should not be called explicitly.  It is called by
        a 'coherence calculator' instance's __call__ method.

        This routine utilizes a model's 'calcCoh' method, which must
        be defined explicitly for all sub-classes of cohModelBase.

        See also
        --------
        calcij - computes the coherence for individual grid-point pairs.

        """
        cohi._crossSpec[cohi._i_diag]=cohi.spec.flat[comp]
        for (ii,jj),indx in cohi._iter_flat_inds:
            if ii!=jj:
                cohi._crossSpec[indx]=self.calcij(cohi,comp,ii,jj)*np.sqrt(cohi.spec.flat[comp,ii]*cohi.spec.flat[comp,jj])
                if cohi.__class__ is cohereCalc: # Mirror the data.
                    cohi._crossSpec[indx[1],indx[0]]=cohi._crossSpec[indx]

    def calcij(self,cohi,comp,ii,jj):
        """
        THIS IS A PLACEHOLDER METHOD WHICH SHOULD BE OVER-WRITTEN FOR ALL SUB-CLASSES
        OF cohModelBase. THIS METHOD ONLY RAISES AN ERROR.
        
        A functioning version of this method (i.e. in a subclass of cohModelBase)
        should return the a length-n_f vector that is the coherence between point
        *ii*=(iz,iy) and *jj*=(jz,jy) for velocity component *comp*.

        Parameters
        ----------
        *cohi*    - A 'coherence calculator' instance (for the given tsrun).
        *comp*    - an integer (0,1,2) indicating the velocity component for which to
                    compute the coherence.
        *ii*,*jj* - Two-integer elements indicating the grid-points between which to
                    calculate the coherence. For example: ii=(1,3),jj=(2,3)

        See also
        --------
        calc - iterates over grid-point pairs and calls calcCoh to compute the full
               cross-spectral matrix.
        
        """
        raise Exception('Subclasses of cohModelBase must overwrite the calcCoh method.')
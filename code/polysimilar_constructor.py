import numpy as np
import cv2
import copy

#for the graphs
from matplotlib import pyplot as plt
import networkx as nx
from networkx.drawing.nx_agraph import to_agraph 

class NotConvergent(Exception):
    pass

BRIGHTEN_CUTOFF=3

def mask(rgbimage, min=3):  #mask of the nonzero pixels of an rgb image
        imhsv=cv2.cvtColor(rgbimage, cv2.COLOR_BGR2HSV)
        return cv2.inRange(imhsv, np.array([0,0,min]),np.array([255,255,255]))

def collision(mask1, mask2):
    if cv2.countNonZero(cv2.bitwise_and(mask1,mask2,mask=mask2))==0:
        return False
    return True

def brighten(im, backgroundIm, cutoff=BRIGHTEN_CUTOFF):
    '''m=mask(im)
    imhsv=cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    for i in range(imhsv.shape[0]):
        for j in range(imhsv.shape[1]):
            imhsv[i,j,2]=200
    im2=cv2.cvtColor(imhsv, cv2.COLOR_HSV2BGR)
    return cv2.bitwise_and(im2, im2, mask=m)
    '''
    m=mask(im, min=cutoff)
    return cv2.bitwise_and(backgroundIm, backgroundIm, mask=m)



class Affine_transform():

    def __init__(self, matrix, translation,probability=1 ): 
        self.m=np.float32(matrix)
        self.t=np.float32(translation)
        self.p=probability
        self.trimat()
        self.blankImage=None
        self.isImageDefined=False

    @classmethod
    def tripoints(cls, originalPoints, modifiedPoints, probability=1):
        tm=cv2.getAffineTransform(np.float32(originalPoints), np.float32(modifiedPoints))
        return cls(tm[:, :1], tm[:,2], probability )
    @classmethod
    def from_trimat(cls, trimat, probability=1):
        return cls(trimat[:,:2],trimat[:,2], probability )

    @classmethod
    def id(cls):
        return cls([[1,0], [0,1]], [0,0], 1)


    def print(self):
        print("matrix=")
        print(str(self.m))
        print("translation vector="+str(self.t))
        print("probability="+str(self.p))

    def trimat(self): #three column matrix (last column is the constant term) used in warp affine
        self.tm=np.array([[self.m[j,i] if i<2 else self.t[j]  for i in range(3)] for j in range(2)])
        return np.array(self.tm)

    def cv2warp(self, img, dimensions=None):
        if dimensions==None:
            dimensions=img.shape[0], img.shape[1]
        #some blur to avoid 1-pixel issue... 
        #there is still some fading issue (we should brighten at each step ?) or some problem with the blur...
        cop=copy.copy(img)
        #cop=cv2.boxFilter(cop,-1,[2,2], normalize=True) 
        im=cv2.warpAffine(cop, self.tm,  [dimensions[0],  dimensions[1]] )
           
        return im

    def apply(self, p):  
        return self.m.dot(p)+self.t

    def __mul__(self, other):
        return Affine_transform(self.m.dot(other.m), self.t+self.m.dot(other.t), self.p*other.p)

    def rescale(self, zerop, scale):  #zerop is expressed in the new scale
        self.m=self.m
        self.t=np.array([scale*self.t[i]+zerop[i]-self.m.dot(zerop)[i] for i in range(2)])
        self.trimat()
    
    def norm(self):
        return np.linalg.norm(self.m, ord=2) #the operator norm (largest singular value)
    
    def limpoint(self):  #limit of f^n(x) for any initial x. Depreciated
        if  max([abs(i) for i in np.linalg.eigvals(self.m)])>=1:
            raise NotConvergent("the stemtrans matrix is of eigenvalues greater than 1")
        return self.scale*( np.linalg.solve(self.m, self.translation) + self.zero_coordinates)


#this class is to define sub-fractals of the clas fdfractal
class Child():
    def __init__(self, name, map, resolution=1,image=None, mask=None):
        self.name = name
        self.map = map
        self.resolution = resolution #this should be smaller than 1
        self.image=image
        self.mask=mask

    def correctResolution(self):
        pass
        self.resolution=self.map.norm()


class Polysimilar(): #finitely decomposable fractal
    #images={"name1":image1, ...}
    #families={"name1":[child1, ....], ....}
    #families["name"] is the list of childs of the fractal "name"
    # for some child in families["name"], child is an instance of the class child,
    # child.name is the name of the child (must be a name in images) 
    # and child.map is the affine_transform used to glue images[child.name] on the fractal "name"
    # and child.resolution tracs wether it is usefull to decompose the childs into the grandchilds
    #currentImageFamily=[ child1, ...] to construct the current image

    def __init__(self,images, families, currentImageDims, currentImageFamily, threshold=1):
        self.originalImages=copy.copy(images)
        self.images=images
        self.families=families
        for name in self.families:
            for child in self.families[name]:
                child.correctResolution()
        self.currentImageFamily=currentImageFamily
        for child in self.currentImageFamily:
            child.correctResolution()
        self.currentImageDims=currentImageDims
        self.threshold=threshold
        #construct the current image and the masks
        self.updateCurrentImage()

        
    def updateChildImage(self, child):
        child.image=child.map.cv2warp(self.images[child.name], dimensions=self.currentImageDims) 
        #we also update (or create) the mask of elem in the current image, as an attribute of the child elem
        child.mask=mask(child.image)
  
    def updateCurrentImage(self):  
        self.currentImage=np.zeros([self.currentImageDims[1], self.currentImageDims[0], 3], np.uint8)
        for child in self.currentImageFamily:
            self.updateChildImage(child)
            self.currentImage=cv2.bitwise_or(self.currentImage, child.image)

    def addChild(self, imageName, child):
        self.families[imageName].append(child)
    
    def grandChilds(self, elem, mask=None):  #elem is a Child object, you can filter by elements intersecting the mask
        grandChilds=[]
        for child in self.families[elem.name]:
            grandchild=Child( child.name,elem.map*child.map, resolution=elem.resolution*child.resolution)
            grandchild.correctResolution()  #in case the most enlarged vectors of elem.map and child.map are not the same
            grandChilds.append(grandchild)
        return grandChilds



    def refineFamily(self, family, mask=None):  #family is a list of Child objects
        refinedFamily=[]
        for child in family:  #elem is a Child object
            if child.resolution>1:
                grandChilds=self.grandChilds(child)
                grandChilds=self.refineFamily(grandChilds, mask=mask)
                refinedFamily.extend(grandChilds)
            else:
                self.updateChildImage(child)
                
                if (mask is not None) or collision(mask, child.mask):
                    refinedFamily.append(child)
        return refinedFamily

    def refineImage(self, name):
        im=np.zeros(self.images[name].shape, np.uint8)
        dim=[im.shape[1], im.shape[0]]
        for elem in self.families[name]:
            im=cv2.bitwise_or(im, elem.map.cv2warp(self.images[elem.name],dim  ))
        self.images[name]=im

    def refineAllImages(self):
        for fracname in self.images:
            self.refineImage(fracname)

    def brightenAllImages(self, cutoff=BRIGHTEN_CUTOFF):
        for name in self.images:
            self.images[name]=brighten(self.images[name], self.originalImages[name], cutoff=cutoff)

    def childOfZoom(self, child, xmin, ymin, zoomcoef):
        t=Affine_transform(zoomcoef*child.map.m, zoomcoef*(child.map.t-[xmin, ymin]), child.map.p )
        return Child(child.name, t, child.resolution*zoomcoef)
                

    def zoomOnPosition(self,x,y, zoomcoef): #[x, y] is the point fixed in the zoom.
        width,height=self.currentImageDims
        xmin, ymin=x-x//zoomcoef, y-y//zoomcoef
        
        #we construct the mask of the box on which we zoom
        whitebox=np.ones([int(height/zoomcoef), int(width/zoomcoef)], np.uint8)
        boxmask=cv2.warpAffine(whitebox, np.array([[1.0,0,xmin], [0,1, ymin]]), [width, height])

        newImageFamily=[]
        for child in self.currentImageFamily:
            if collision(child.mask, boxmask):
                newChild=self.childOfZoom(child, xmin, ymin, zoomcoef)
                self.updateChildImage(newChild)
                newImageFamily.append(newChild)
        self.currentImageFamily=self.refineFamily(newImageFamily, mask=boxmask)
        self.updateCurrentImage()

    def graph(self):
        edges=[]
        i=0
        for im in self.families:
            for child in self.families[im]:
                edges.append((im, child.name))
                i+=1
       
        G=nx.MultiDiGraph(edges)
        pos=nx.spring_layout(G)
        nx.draw_networkx(G)
        
        plt.show()






def zoomeffect(x, y, img1, img2, coeff, windowname, Nframes, sleeptime, stepbystep=False): #img2 is the zommed imaged with fixed point at x, y, of same size as img
    img=copy.copy(img1)
    width, height=img.shape[1], img.shape[0]
    scales=[1+(coeff-1)*i/Nframes for i in range(Nframes)]
    for h in scales:
        xmin, ymin=[int(a*(1-h/coeff)) for a in [x, y]]
        smallsize=[int(i) for i in [width*h/coeff, height*h/coeff]]
        xmax, ymax=[xmin+smallsize[0],ymin+smallsize[1]]
        img=cv2.warpAffine(img1, np.array([[h, 0, (1-h)*x], [0, h, (1-h)*y]]), [width, height])
        
        img[ymin:ymax, xmin:xmax]=cv2.warpAffine(copy.copy(img2), np.array([[h/coeff, 0, 0], [0, h/coeff, 0]]), smallsize)
        cv2.imshow(windowname, img)
        if stepbystep:
            while True:
                if cv2.waitKey(1)==ord('s'):
                    break
        else:
            if cv2.waitKey(sleeptime)==ord('q'):
                break
        

         




#tests
if __name__ == '__main__':



  
    zoomcoef=5
    zoomframes=50
    zoomwait=30
       
    halfid=[[0.5,0], [0,0.5]]
    id=Affine_transform([[1,0], [0,1]], [0,0], 1)
    #the fern maps
    t2=Affine_transform([[0.85, 0.04], [-0.04, 0.85]], [0, 1.6], 0.73)
    t3=Affine_transform([[-0.15, 0.28],[0.26, 0.24] ], [0,0.16], 0.13)
    t4=Affine_transform([[0.2, -0.26],[0.23, 0.22]], [0,0.44], 0.11)
    #sierpinsky maps
    s1=Affine_transform(halfid,[0,0] )
    s2=Affine_transform(halfid, [1/2, 0])
    s3=Affine_transform(halfid, [1/4,np.sqrt(3)/4])
     #the dragon maps
    dr1 = Affine_transform([[0.5, -0.5], [0.5, 0.5]], [0, 0])
    dr2 = Affine_transform([[-0.5, 0.5], [-0.5, -0.5]], [0, 1])
    dragonscale = 70
    dragonzerop = [int(dragonscale*i) for i in [3, 3]]
    [d.rescale(dragonzerop, 300) for d in [dr1, dr2]]
    d=[dr1, dr2]
    #rescaling fern and sierpinsky
    scale=100
    zerop=[int(scale*i) for i in [3, 0] ]
    width, height=[int(scale*i) for i in [6,11]]
    [t.rescale(zerop, scale) for t in [ t2, t3, t4]]
    [s.rescale([0,3*70], 6*70) for s in [s1, s2, s3]]    
    t=[t2, t3, t4]
    color=[250,10,20]
    s=[s1, s2, s3]

    families={}
    images={}
    blankImage=np.array([[color for i in range(width)] for j in range(height)], np.uint8)
    for j in range(1):
        families.update({"sierp"+str(j):[Child("sierp"+str(j+1),s[i], 1) for i in range(3)] })
        images.update({"sierp"+str(j): copy.copy(blankImage) })
    families.update({"sierp"+str(j+1):[Child("dragon0", s[i], 1) for i in range(1)]+[Child("sierp"+str(j+1), s[i], 1) for i in range(1,3)]})
    images.update({"sierp"+str(j+1):  copy.copy(blankImage) })


    for j in range(10):
        families['dragon'+str(j)]=[Child("dragon"+str(j+1), d[i], 1) for i in range(2)]
        images['dragon'+str(j)]=copy.copy(blankImage)
    families['dragon'+str(j+1)]=[Child("sierp0", d[i], 1) for i in range(2)]
    images['dragon'+str(j+1)]=copy.copy(blankImage)

        
   
    currentImageFamily=[Child("sierp0", id, 1)]
    frac=Polysimilar(images, families,[width, height], currentImageFamily )
    #frac.graph()


    image=frac.currentImage

    cv2.imshow("image",image )
    cv2.moveWindow("image", 30,60)

    def zoom(event, x, y, flags, param):
        global image
        if event==cv2.EVENT_LBUTTONDOWN:
            frac.zoomOnPosition(x, y, zoomcoef)
            zoomeffect(x,y,image , frac.currentImage, zoomcoef, "image", zoomframes, zoomwait)
            image=frac.currentImage
            cv2.imshow("image", image)

    cv2.setMouseCallback("image", zoom)


    while True:
        key=cv2.waitKey(1)
        if key==ord('q'):
            break
        if key==ord('n'):
            frac.refineAllImages()
            frac.updateCurrentImage()
            image=frac.currentImage
            cv2.imshow("image", image)

import PySimpleGUI as sg
import cv2
import numpy as np
import polysimilar_constructor as f
import copy
import time


FRACTAL_COLOR=[176,212,48]
LINE_COLOR="purple"
POINT_COLOR="blue"
LINEWIDTH=2
DIAGWIDTH=1
ZOOMNFRAMES=30
ZOOMSLEEP=0.01


class Point():
    def __init__(self, pos,graph, color="blue", linecolor="white" ):
        self.color = color
        self.linecolor=linecolor
        self.pos=np.array(pos)
        self.graph=graph
        self.elem=graph.draw_circle((pos[0], pos[1]), 5, fill_color=color, line_color=self.linecolor)
        self.anchorpos=pos

    def relocate(self, newpos):
        self.graph.delete_figure(self.elem)
        self.pos=newpos
        self.elem=self.graph.draw_circle((newpos[0], newpos[1]), 5, fill_color=self.color, line_color=self.linecolor)

    def translate(self, delta): #translate from anchorpos
        self.graph.delete_figure(self.elem)
        self.pos=delta+self.anchorpos
        self.elem=self.graph.draw_circle((self.pos[0], self.pos[1]), 5, fill_color=self.color, line_color=self.linecolor)

    def isclicked(self, pos):
        dist=np.sqrt((pos[0]-self.pos[0])**2+(pos[1]-self.pos[1])**2)
        return dist<=5

class Cross():
    def __init__(self, pos, graph, color="red"):
        self.color = color
        self.pos=np.array(pos)
        self.graph=graph
        self.draw()
    
    def draw(self):
        crosslength=10
        self.cross1=self.graph.draw_line(tuple(self.pos-[0,crosslength]), tuple(self.pos+[0,crosslength]), color=self.color, width=3)
        self.cross2=self.graph.draw_line(tuple(self.pos-[crosslength,0]), tuple(self.pos+[crosslength,0]), color=self.color, width=3)

    def relocate(self, newpos):
        newpos=np.array(newpos)
        self.graph.delete_figure(self.cross1)
        self.graph.delete_figure(self.cross2)
        self.pos=newpos
        self.draw()


class Tile():
    def __init__(self, zeropos, pos1, pos2, graph, name=None, color=POINT_COLOR, linecolor=LINE_COLOR, child=None):
        self.name=name
        self.child=child
        self.graph=graph
        self.linecolor=linecolor
        self.pos3=[pos1[i]+pos2[i]-zeropos[i] for i in range(2)]
        self.zeropoint=Point(zeropos, graph, color=color)
        self.point1=Point(pos1, graph, color=color)
        self.point2=Point(pos2, graph, color=color)
        self.point3=Point(self.pos3, graph, color=color)
        self.points=[self.zeropoint, self.point1, self.point2, self.point3]
        self.grasped=None
        self.drawlines()

    def affineTrans(self, box0, dimBox):
        initPoints=[ [0, 0], [ dimBox[0], 0], [0, dimBox[1]]]
        initPoints=np.float32([np.float32(p) for p in initPoints])
        currentPointsList=np.float32([self.points[i].pos-np.float32(box0) for i in range(3)])
        mat=cv2.getAffineTransform(initPoints, currentPointsList)
       
        
        return mat

    def drawlines(self):
        self.line1=self.graph.draw_line(tuple(self.zeropoint.pos), tuple(self.point1.pos), color=self.linecolor, width=LINEWIDTH)
        self.line2=self.graph.draw_line(tuple(self.zeropoint.pos), tuple(self.point2.pos), color=self.linecolor, width=LINEWIDTH)
        self.line3=self.graph.draw_line(tuple(self.point3.pos), tuple(self.point1.pos), color=self.linecolor, width=LINEWIDTH)
        self.line4=self.graph.draw_line(tuple(self.point3.pos), tuple(self.point2.pos), color=self.linecolor, width=LINEWIDTH)
        self.diag=self.graph.draw_line(tuple(self.zeropoint.pos), tuple(self.point3.pos), color=self.linecolor, width=DIAGWIDTH)
        crosslength=3
        self.cross1=self.graph.draw_line(tuple(self.zeropoint.pos-[0,crosslength]), tuple(self.zeropoint.pos+[0,crosslength]), color="red", width=3)
        self.cross2=self.graph.draw_line(tuple(self.zeropoint.pos-[crosslength,0]), tuple(self.zeropoint.pos+[crosslength,0]), color="red", width=3)

    def eraselines(self):
        for l in [self.line1, self.line2, self.line3, self.line4, self.diag, self.cross1, self.cross2]:
            self.graph.delete_figure(l)

    def startmove(self, mousePos):
        self.originalMousePos=np.array(mousePos)
        for p in self.points:
            p.anchorpos=p.pos

    def zeromove(self, mousePos):
        delta=np.array(mousePos)-self.originalMousePos
        for p in self.points:
            p.translate(delta)
        self.eraselines()
        self.drawlines()

    def move12(self, mousePos, num):
        delta=np.array(mousePos)-self.originalMousePos
        p=self.points[num]
        p.translate(delta)
        self.point3.translate(delta)
        self.eraselines()
        self.drawlines()

    def move3(self, mousePos):
        delta=np.array(mousePos)-self.originalMousePos
        self.point3.translate(delta)
        x, y=self.point3.anchorpos-self.zeropoint.pos
        nx, ny=self.point3.pos-self.zeropoint.pos
        c=(nx*x+ny*y)/(x**2+y**2)
        s=(x*ny-y*nx)/(x**2+y**2)
        def sim(pos):
            a, b=[pos[i]-self.zeropoint.pos[i] for i in range(2)]
            return [c*a-s*b+self.zeropoint.pos[0], s*a+c*b+self.zeropoint.pos[1]]
        self.point1.relocate(sim(self.point1.anchorpos))
        self.point2.relocate(sim(self.point2.anchorpos))
        self.eraselines()
        self.drawlines()

    def mousePressed(self,key, values):
        val=values[key]
        if self.grasped==None:
            for i in range(4):
                if self.points[i].isclicked(val):
                    self.grasped=i
                    self.startmove(val)
        elif self.grasped==0:
            self.zeromove(val)
        elif self.grasped in [1, 2]:
            self.move12(val, self.grasped)
        elif self.grasped==3:
            self.move3(val)
        return self.grasped
    
    def mouseReleased(self):
        self.grasped=None

class Anvil():
    def __init__(self, name, dimSpace, dimBox, box0,tilePositions=None, numberOfTiles=0, image=None):
        self.name = name
        self.dimSpace=dimSpace
        self.dimBox=dimBox
        self.box0=box0
        #define the tilePositions
        if tilePositions:
            self.tilePositions=tilePositions
        else:
            self.tilePositions=[]
            for i in range(numberOfTiles):
                self.tilePositions.append( [[10*i+self.box0[0], 10*i+self.box0[1]],[10*i+self.box0[0]+self.dimBox[0], 10*i+self.box0[1]],[10*i+self.box0[0], 10*i+self.box0[1]+self.dimBox[1]]] )
        #construct the initial image. This image should not be modified, just copied. The current image to display will be in the Polysimilar object "frac", at frac.images[anvil.name]
        if image:
            self.image=image 
        else:
            #self.image=255*np.ones([dimBox[1], dimBox[0], 3], np.uint8)
            self.image=np.array([[ FRACTAL_COLOR for i in range(dimBox[0]) ] for j in range(dimBox[1])], np.uint8)
        self.graph_image=None #this will be an image on the graph, to be created by the forge when the window is finalized.

    def layout(self, anvilNames):
        graph_layout=[[sg.Graph(self.dimSpace, (0, self.dimSpace[1]), (self.dimSpace[0], 1), key="graph_"+self.name, enable_events=True, drag_submits=True)]]
        line_layout=[[sg.Text("map"+str(i)+" Origin", key=self.name+str(i)+"text")] +\
        [sg.Combo(anvilNames,default_value=self.name, key="origin_"+self.name+str(i)) ] \
         for i in range(len(self.tilePositions))]
        layout=[[sg.Frame("",graph_layout)] ,\
            [sg.Col(line_layout, size=(self.dimSpace[0], 100), scrollable=True)],\
            [sg.Button("Open zooming window", key="zoomingActivation_"+self.name),sg.Text(" Multiply size by : "), sg.Combo([1+i/10 for i in range(20)], key="multiplier_"+self.name, default_value=1.0)]]
        return layout

    def setTiles(self,graph):
        self.tiles=[Tile(self.tilePositions[i][0], self.tilePositions[i][1], self.tilePositions[i][2], graph, name="map_"+self.name+str(i), child=self.name) for i in range(len(self.tilePositions))]

    def getMatrix(self, tile, childBox0=None, childDimBox=None):
        if childBox0==None:
            childBox0=self.box0
            childDimBox=self.dimBox
        return tile.affineTrans(childBox0, childDimBox)

class Forge():
    def __init__(self, anvils, dimensions, maxIterations=1, brightenOn=False):
        self.anvils=anvils
        self.dimensions=dimensions
        self.maxIterations=maxIterations
        self.iterationsCounter=0
        self.brightenOn=brightenOn
 
    def makeWindows(self):
        anvilNames=[anvil.name for anvil in self.anvils]
        anvils_line=[[ sg.Frame("Anvil "+anvil.name, anvil.layout(anvilNames), font="Any 12", title_color="white") for anvil in self.anvils]]
        win=sg.Window("Forge", [[[sg.Text("Warning, zooming may freeze if the maps are too large or overlap too much. Too be improved...")]],\
            [sg.Col(anvils_line, size=(self.dimensions[0], self.dimensions[1]-100), scrollable=True) ], \
            [sg.Button(button_text="Reset Images", key="reset"),\
            sg.Button(button_text="Iterate", key="iterate", size=(6,1)) ]])
        win.Finalize()
        for anvil in self.anvils:
            anvil.setTiles(win["graph_"+anvil.name])
        self.win=win
        return win

    def makeFractal(self):
        images={}
        families={}
        currentImageDims=[self.anvils[0].dimBox[i] for i in range(2)]
        currentImageFamily=[f.Child("A", f.Affine_transform.id())]
        for anvil in self.anvils:
            images[anvil.name]=copy.copy(anvil.image)
            families[anvil.name]=[f.Child(tile.child, f.Affine_transform.from_trimat(anvil.getMatrix(tile))) for tile in anvil.tiles]
        frac=f.Polysimilar(images, families, currentImageDims, currentImageFamily)
        self.frac=frac

    def update(self):
        for anvil in self.anvils:
            graph=self.win["graph_"+anvil.name]
            imgbytes=cv2.imencode('.ppm', self.frac.images[anvil.name])[1].tobytes()
            if anvil.graph_image:
                graph.delete_figure(anvil.graph_image)  
            anvil.graph_image = graph.draw_image(data=imgbytes, location=(anvil.box0[0],anvil.box0[1]))    # draw new image
            graph.send_figure_to_back(anvil.graph_image)

    def updateFractalMap(self, anvil, tileNumber):
            child=self.frac.families[anvil.name][tileNumber]
            tile=anvil.tiles[tileNumber]
            for anvil2 in self.anvils:
                if anvil2.name==tile.child:
                    box0=anvil2.box0
                    dimBox=anvil2.dimBox
                    break
            child.map=f.Affine_transform.from_trimat(anvil.getMatrix(tile, childBox0=box0, childDimBox=dimBox))

    def updateFractalOrigin(self, anvil, tileNumber, value):
        tile=anvil.tiles[tileNumber]
        child=self.frac.families[anvil.name][tileNumber]
        newOrigin=value["origin_"+anvil.name+str(tileNumber)]
        tile.child=newOrigin
        child.name=newOrigin


    def reactEvent(self,event, value):
        if event!="__TIMEOUT__":
            print(event)
        for anvil in self.anvils:
            for tileNumber in range(len(anvil.tiles)):
                self.updateFractalOrigin(anvil, tileNumber, value)
                self.update()
        for anvil in self.anvils:
            if event=="zoomingActivation_"+anvil.name:
                zoomWindow(self.frac,anvil.name, float(value["multiplier_"+anvil.name]))
                self.frac.currentImageFamily=[f.Child(anvil.name, f.Affine_transform.id())]
                
                break
        if event=="reset":
            self.resetImages()
        elif event=="iterate":
            self.frac.refineAllImages()
            self.update()
        elif event=="new_anvil_but":
            return True 
        else:
            for anvil in self.anvils:
                if event=="graph_"+anvil.name:
                    self.mousePressed(anvil, value)
                    self.frac.brightenAllImages()
                elif event=="graph_"+anvil.name+"+UP":
                    self.mouseReleased(anvil, value)
        return False
        


    def mousePressed(self, anvil, value):
        i=0
        for tile in anvil.tiles:
            if tile.mousePressed("graph_"+anvil.name, value)!=None:
                self.updateFractalMap(anvil, i)
                self.iterationsCounter=0
                self.win[anvil.name+str(i)+"text"].update("X map"+str(i)+" Origin")
                break
            i+=1

    def mouseReleased(self, anvil,value):
        i=0
        for tile in anvil.tiles:
            self.win[anvil.name+str(i)+"text"].update("map"+str(i)+" Origin")
            tile.mouseReleased()
            i+=1

    def resetImages(self):
        self.iterationsCounter=0
        for anvil in self.anvils:
            self.frac.images[anvil.name]=copy.copy(anvil.image)

def zoomWindow(fractal, imageName, sizeScaling):
    originalDimensions=fractal.images[imageName].shape[:2]
    print(imageName)
    imageDimensions=[int(sizeScaling*a) for a in originalDimensions]
    print(imageDimensions)
    fractal.currentImageDims=[imageDimensions[1], imageDimensions[0]]
    fractal.currentImageFamily=[f.Child(imageName, f.Affine_transform.id())]
    fractal.updateCurrentImage()
    fractal.zoomOnPosition(0,0, sizeScaling)
    layout=[[sg.Graph((imageDimensions[1], imageDimensions[0]), (0, imageDimensions[0]), (imageDimensions[1], 0), key="zoom_graph", enable_events=True )],\
    [sg.Button("Start Zooming", key="zoom_but")]]
    win=sg.Window("Zooming", layout)
    graph=win["zoom_graph"]
    win.Finalize()

    target=Cross([10,10], graph)

    zooming=False
    zoomcoef=1
    zoomEach=1.02
    zoomStep=1.3
    im=copy.copy(fractal.currentImage)
    imgbytes=cv2.imencode(".ppm", im )[1].tobytes()
    graph_image=graph.draw_image(data=imgbytes, location=[0,0])
    graph.send_figure_to_back(graph_image)
    while True:
        event, value=win.read(timeout=1)
        if event in ('Exit', None):
            break
        if event=="zoom_but":
            if zooming==False:
                zooming=True
                win["zoom_but"].update("Stop zooming")
            else:
                zooming=False
                win["zoom_but"].update("Start zooming")
        if event=="zoom_graph":
            target.relocate(value["zoom_graph"])
        if zooming:
            if zoomcoef<zoomStep:
                zoomcoef=zoomcoef*zoomEach
                im=cv2.warpAffine(copy.copy(fractal.currentImage), np.array([[zoomcoef, 0, (1-zoomcoef)*target.pos[0]], [0, zoomcoef, (1-zoomcoef)*target.pos[1]]]), [imageDimensions[1], imageDimensions[0]] )
            else:
                zoomcoef=1
                fractal.zoomOnPosition(target.pos[0], target.pos[1], zoomStep)
                im=copy.copy(fractal.currentImage)
        graph.delete_figure(graph_image)
        imgbytes=cv2.imencode(".ppm", im )[1].tobytes()
        graph_image=graph.draw_image(data=imgbytes, location=[0,0])
        graph.send_figure_to_back(graph_image)
        time.sleep(ZOOMSLEEP)
            



        
def main_loop(forge):
    win=forge.makeWindows()
    forge.makeFractal()
    forge.update()

    while True:
        event, value = win.read(timeout=0)
        if event in ('Exit', None):
            break
        forge.reactEvent(event, value)
        if forge.iterationsCounter<forge.maxIterations:
            forge.frac.refineAllImages()
            forge.iterationsCounter+=1
        if forge.brightenOn:
                forge.frac.brightenAllImages()
        forge.frac.updateCurrentImage()
        forge.update()






if __name__ == '__main__':

    anvilWidth=400
    anvilHeight=500
    imageWidth=275
    imageHeight=375
    imageZero=[50,50]

    anvil2Width=400
    anvil2Height=400
    image2Width=275
    image2Height=275
    image2Zero=[50,50]

    winWidth=1024
    winHeight=768


    anvil=Anvil("A", (anvilWidth, anvilHeight), (imageWidth, imageHeight), imageZero, numberOfTiles=3)
    anvil2=Anvil("B", (anvil2Width, anvil2Height), (image2Width, image2Height), image2Zero, numberOfTiles=2)
    forge=Forge([anvil, anvil2],[winWidth,winHeight ])
    
    main_loop(forge)

   #main loop     
    

    




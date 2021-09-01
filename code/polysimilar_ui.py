import PySimpleGUI as sg
import cv2
import numpy as np
import polysimilar_constructor as f
import copy
import time
import re
import screeninfo


FRACTAL_COLOR=[254,102,198]
LINE_COLOR="white"
POINT_COLOR="blue"

POINT_RADIUS=7
ACTIVATED_POINT_RADIUS=10
LINEWIDTH=2
DIAGWIDTH=1
ZOOMNFRAMES=30
ZOOMSLEEP=0.01

MAX_MAPS_PER_ANVILS=5
MAX_ANVILS=16

monitor=screeninfo.get_monitors()[0]
MONITOR_WIDTH, MONITOR_HEIGHT=monitor.width, monitor.height



sg.theme('darkGrey3')

GRAPH_BACKGROUND_COLOR="dim grey"


class Point():
    def __init__(self, pos,graph, color="blue", linecolor="white", normalPointRadius=POINT_RADIUS, activatedPointRadius=ACTIVATED_POINT_RADIUS  ):
        self.color = color
        self.linecolor=linecolor
        self.pos=np.array(pos)
        self.graph=graph
        self.pointRadius=normalPointRadius
        self.normalPointRadius=normalPointRadius
        self.activatedPointRadius=activatedPointRadius
        self.elem=graph.draw_circle((pos[0], pos[1]), self.pointRadius, fill_color=color, line_color=self.linecolor)
        self.anchorpos=pos
        

    def relocate(self, newpos):
        self.graph.delete_figure(self.elem)
        self.pos=np.array(newpos)
        self.elem=self.graph.draw_circle((newpos[0], newpos[1]), self.pointRadius, fill_color=self.color, line_color=self.linecolor)

    def translate(self, delta): #translate from anchorpos
        self.graph.delete_figure(self.elem)
        self.pos=delta+self.anchorpos
        self.elem=self.graph.draw_circle((self.pos[0], self.pos[1]), self.pointRadius, fill_color=self.color, line_color=self.linecolor)

    def erase(self):
        self.graph.delete_figure(self.elem)

    def isclicked(self, pos):
        dist=np.sqrt((pos[0]-self.pos[0])**2+(pos[1]-self.pos[1])**2)
        return dist<=5

    def activate(self):
        self.pointRadius=self.activatedPointRadius

    def deactivate(self):
        self.pointRadius=self.normalPointRadius
        self.graph.delete_figure(self.elem)
        self.elem=self.graph.draw_circle((self.pos[0], self.pos[1]), self.pointRadius, fill_color=self.color, line_color=self.linecolor)

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
        self.grasped=None  #when grasped, this is the number of the grasped point (0,1,2,3)
        #a regular expression pattern to modify the map from keyboard input
        self.repattern=re.compile(r'Mp0x_(?P<x0>\d+)_y_(?P<y0>\d+)_p1x_(?P<x1>\d+)_y_(?P<y1>\d+)_p2x_(?P<x2>\d+)_y_(?P<y2>\d+)$')
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

    def erase(self):
        self.eraselines()
        for point in self.points:
            point.erase()

    def startmove(self, mousePos):
        self.originalMousePos=np.array(mousePos)
        for p in self.points:
            p.anchorpos=p.pos
            p.activate()

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
        for p in self.points:
            p.deactivate()
        self.eraselines()
        self.drawlines()

    def __str__(self):
        return "Mp0x_"+str(int(self.zeropoint.pos[0]))+"_y_"+str(int(self.zeropoint.pos[1]))+\
               "_p1x_"+str(int(self.point1.pos[0]))+   "_y_"+str(int(self.point1.pos[1]))+\
               "_p2x_"+str(int(self.point2.pos[0]))+   "_y_"+str(int(self.point2.pos[1]))

    def modify_from_string(self, string):
        m=self.repattern.search(string)
        if m:
            x0,y0, x1, y1, x2, y2=[int(i) for i in m.group('x0', 'y0', 'x1', 'y1', 'x2', 'y2')]
            self.zeropoint.relocate([x0,y0])
            self.point1.relocate([x1, y1])
            self.point2.relocate([x2,y2])
            self.point3.relocate([-x0+x1+x2, -y0+y1+y2])
            self.eraselines()
            self.drawlines()
            return True
        else:
            return False
    
    def rectify(self, width, height):  #when a map is rectified it preserves the aspect ratio of its child. However it can be flipped
        self.zeropoint.anchorpos=self.zeropoint.pos
        det=np.linalg.det(self.affineTrans([0,0], [1,1])[:2,:2])
        if det>0:
            sign=1
        else:
            sign=-1
        self.point1.anchorpos=self.zeropoint.pos+[sign*width,0]
        self.point2.anchorpos=self.zeropoint.pos+[0,height]
        self.point3.anchorpos=self.point1.anchorpos+self.point2.anchorpos-self.zeropoint.anchorpos
        self.originalMousePos=self.point3.anchorpos
        self.move3(self.point3.pos)


class Anvil():
    def __init__(self, name, dimSpace, dimBox, box0,tilePositions=None, numberOfTiles=0, image=None, maxNumberOfTiles=MAX_MAPS_PER_ANVILS):
        self.name = name #the name should not end or start by a number and not contain '_'
        self.dimSpace=dimSpace
        self.dimBox=dimBox
        self.box0=box0
        self.numberOfTiles=numberOfTiles
        self.maxNumberOfTiles=maxNumberOfTiles
        #define the tilePositions
        if tilePositions:
            self.tilePositions=tilePositions
        else:
            self.tilePositions=[]
            for i in range(self.maxNumberOfTiles):
                self.tilePositions.append( [[10*i+self.box0[0], 10*i+self.box0[1]],[10*i+self.box0[0]+self.dimBox[0], 10*i+self.box0[1]],[10*i+self.box0[0], 10*i+self.box0[1]+self.dimBox[1]]] )
        #define the childs as self.name. This may be changed and saved, usefull when reopening the windows
        self.tilesChilds=[]
        for i in range(maxNumberOfTiles):
            self.tilesChilds.append(self.name)
        #construct the initial image. This image should not be modified, just copied. The current image to display will be in the Polysimilar object "frac", at frac.images[anvil.name]
        if image:
            self.image=image 
        else:
            #self.image=255*np.ones([dimBox[1], dimBox[0], 3], np.uint8)
            self.image=np.array([[ FRACTAL_COLOR for i in range(dimBox[0]) ] for j in range(dimBox[1])], np.uint8)
        self.graph_image=None #this will be an image on the graph, to be created by the forge when the window is finalized.

        #we construct a pattern (coupled with the __str__ method and used in the "edit" method) for loading a save from a string. Also coupled with the tile __str__ method...
        repatternString=r"An_(?P<numtiles>\d+)_gW_(?P<gw>\d+)_H_(?P<gh>\d+)"+\
            r"_iW_(?P<iw>\d+)_H_(?P<ih>\d+)_ZX_(?P<zx>\d+)_Y_(?P<zy>\d+)"+\
            r"(?P<maps>(_\d*Mp0x_\d+_y_\d+_p1x_\d+_y_\d+_p2x_\d+_y_\d+)*)"
        self.repattern=re.compile(repatternString)
        self.tiles=[] #to be completed when calling setTiles
  
    def regularName(self, name):
        if not name:
            return False
        if re.search('^\d.*|.*\d$|_', name):
            sg.popup('A name must not start or end by a number nor contain underscore')
            return False
        else:
            return True
    def layout(self, anvilNames):
        graph_layout=sg.Graph(self.dimSpace, (0, self.dimSpace[1]), (self.dimSpace[0], 1), key="graph_"+self.name, enable_events=True, drag_submits=True,  background_color=GRAPH_BACKGROUND_COLOR)
        line_layout=[[sg.Button(button_text='Add map', key='add_map_but'+self.name), sg.Button(button_text='Remove map', key='remove_map_but'+self.name)]]+\
        [[sg.Text("_"+str(i)+" Origin", key=self.name+str(i)+"text"),\
        sg.Combo(anvilNames,default_value=self.tilesChilds[i], key="origin_"+self.name+str(i)) ,\
        sg.Button(button_text='Rectify', key='rectify_but'+self.name+str(i) ),\
        sg.Button(button_text='Edit', key='edit_but'+self.name+str(i)),\
        sg.Input( key="input"+self.name+str(i), size=(42,None))] \
         for i in range(self.maxNumberOfTiles)]
        
        layout=[[graph_layout] ,\
            [sg.Frame('Maps',line_layout)],\
            [sg.Button("Open zooming window", key="zoomingActivation_"+self.name),sg.Text(" Multiply size by : "), sg.Combo([1+i/10 for i in range(20)], key="multiplier_"+self.name, default_value=1.0),\
                sg.Button('Save Anvil', key='save_'+self.name), sg.Button('Load Anvil', key='load_'+self.name), sg.Button('Remove Anvil', key='remove_'+self.name)]]
        return layout

    def setTiles(self,graph):
        self.tiles=[Tile(self.tilePositions[i][0], self.tilePositions[i][1], self.tilePositions[i][2], graph, name="map_"+self.name+str(i), child=self.tilesChilds[i]) for i in range(self.numberOfTiles)]

    def save(self):
        for i in range(len(self.tiles)):
            self.tilePositions[i]=[self.tiles[i].zeropoint.pos, self.tiles[i].point1.pos, self.tiles[i].point2.pos]
            self.tilesChilds[i]=self.tiles[i].child

    def getMatrix(self, tile, childBox0=None, childDimBox=None):
        if childBox0==None:
            childBox0=self.box0
            childDimBox=self.dimBox
        return tile.affineTrans(childBox0, childDimBox)

    def __str__(self):
        string="An_"+str(self.numberOfTiles)+"_gW_"+str(self.dimSpace[0])+"_H_"+str(self.dimSpace[1]) \
            +"_iW_"+str(self.dimBox[0])+"_H_"+str(self.dimBox[1])+"_ZX_"+str(self.box0[0])+"_Y_"+str(self.box0[1])
        for i in range(self.numberOfTiles):
            string+="_"+str(i)+str(self.tiles[i])
        return string

class Forge():
    def __init__(self, anvils, dimensions, maxIterations=1, brightenOn=False, maxNumberOfAnvils=MAX_ANVILS):
        self.anvils=anvils
        self.dimensions=dimensions
        self.maxIterations=maxIterations
        self.iterationsCounter=0
        self.brightenOn=brightenOn
        self.maxNumberOfAnvils=maxNumberOfAnvils

    def makeWindows(self):
        #this creates the main window and returns it to be used in the main loop
        anvilNames=[anvil.name for anvil in self.anvils]
        anvils_line=[[ sg.Frame("Anvil "+anvil.name, anvil.layout(anvilNames), font="Any 12", title_color="white", key="anvil_"+anvil.name) for anvil in self.anvils]]
        win=sg.Window("Forge", [[[sg.Text("Warning, zooming may freeze if the maps are too large or overlap too much. Too be improved...")]],\
            [sg.Col(anvils_line, size=(self.dimensions[0], self.dimensions[1]-50), scrollable=True) ], \
            [sg.Button(button_text="Reset Images", key="reset"),\
            sg.Button(button_text="Iterate", key="iterate", size=(6,1)),\
            sg.Button(button_text="Brighten", key="brighten"),\
            sg.Text('Brighten cutoff:'),\
            sg.Slider(range=(1,254), default_value=1, key="brighten_slider", enable_events=True, orientation='h'),\
            sg.Button('Add Anvil', key='add_anvil'),\
            sg.Button(button_text='reopen', key='reopen'),\
            sg.Button('Save Forge', key='saveForge'), \
            sg.Button('Load Forge', key='loadForge') ]] )
        
        win.Finalize()

        #hiding the unused maps
        for anvil in self.anvils:
            for i in range(anvil.numberOfTiles, anvil.maxNumberOfTiles):
                win[anvil.name+str(i)+"text"].hide_row()
            anvil.setTiles(win["graph_"+anvil.name])
        self.win=win
        return win

    def reopenWindows(self):
        for anvil in self.anvils:
            anvil.save()
        self.win.Close()
        return self.makeWindows()

    def makeFractal(self):
        images={}
        families={}
        currentImageDims=[self.anvils[0].dimBox[i] for i in range(2)]
        currentImageFamily=[f.Child(self.anvils[0].name, f.Affine_transform.id())]
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
            found=False
            for anvil2 in self.anvils:
                if anvil2.name==tile.child:
                    box0=anvil2.box0
                    dimBox=anvil2.dimBox
                    found=True
                    break
            if not found:
                sg.popup('bypassing a misterious bug. Carry on')
                return 0
            child.map=f.Affine_transform.from_trimat(anvil.getMatrix(tile, childBox0=box0, childDimBox=dimBox))
            self.win["input"+anvil.name+str(tileNumber)].update(str(tile))

    def updateFractalOrigin(self, anvil, tileNumber, value):
        tile=anvil.tiles[tileNumber]
        child=self.frac.families[anvil.name][tileNumber]
        newOrigin=value["origin_"+anvil.name+str(tileNumber)]
        tile.child=newOrigin
        child.name=newOrigin

    def add_map(self,anvil):
        i=anvil.numberOfTiles
        newin=self.win #may or may not be modified
        if i==anvil.maxNumberOfTiles:
            text=sg.popup_get_text('You already have the maximum number of maps ! We need to reload to add maps. How many maps do you want to add ?',default_text=1)
            if text:
                if not(re.search('\d+$', text)):
                    sg.popup('Not a valid number')
                else:
                    nAdd=int(text)
                    for i in range(anvil.maxNumberOfTiles,anvil.maxNumberOfTiles+nAdd):
                        anvil.tilePositions.append( [[10*i+anvil.box0[0], 10*i+anvil.box0[1]],[10*i+anvil.box0[0]+anvil.dimBox[0], 10*i+anvil.box0[1]],[10*i+anvil.box0[0], 10*i+anvil.box0[1]+anvil.dimBox[1]]] )
                        anvil.tilesChilds.append(anvil.name)
                        self.frac.addChild(anvil.name, f.Child(anvil.tilesChilds[i], f.Affine_transform.id()))
            #we adjust the number of tiles
                anvil.numberOfTiles+=nAdd
                anvil.maxNumberOfTiles+=nAdd
                newin=self.reopenWindows()
                return newin
        else:
            anvil.numberOfTiles+=1
            self.win[anvil.name+str(i)+"text"].unhide_row()
            anvil.tiles.append(Tile(anvil.tilePositions[i][0], anvil.tilePositions[i][1], anvil.tilePositions[i][2], self.win['graph_'+anvil.name], name="map_"+anvil.name+str(i), child=anvil.tilesChilds[i]))
            self.frac.addChild(anvil.name, f.Child(anvil.tilesChilds[i], f.Affine_transform.id()))
            self.updateFractalMap( anvil, i)
        return newin

    def remove_map(self, anvil):
        i=anvil.numberOfTiles
        if i==0:
            sg.popup('No map to remove !')
        else:
            anvil.save()
            self.win[anvil.name+str(i-1)+'text'].hide_row()
            anvil.tiles[i-1].erase()
            anvil.tiles=anvil.tiles[:-1]
            self.frac.families[anvil.name]=self.frac.families[anvil.name][:-1]
            anvil.numberOfTiles+=-1

    def load_anvil(self, anvil, text=None):
        if not text:
            text=sg.popup_get_text('Copy the anvil text string you want to load', size=(100, None))
        if not(text):
            return False
        m=anvil.repattern.search(text)
        
        if not m:
            sg.popup('Not a valid anvil save string !')
        else:
            number_of_tiles=int(m.group('numtiles'))
            #preparing the maps data, if something goes wrong better if it happens now
            mapstrings=m.group("maps")
            repatternstring=""
            for i in range(number_of_tiles):
                repatternstring+=r"(?P<map"+str(i)+r">_\d*Mp0x_\d+_y_\d+_p1x_\d+_y_\d+_p2x_\d+_y_\d+)"
            mapsPattern=re.compile(repatternstring)
            m2=mapsPattern.search(mapstrings)
            if not m2:
                sg.Popup('Not a valid save string, probably missing some maps')
                return None
            #eventually modifying the graph dimensions and the number of maps
            gw, gh, iw, ih, zx, zy=[int(string) for string in m.group('gw', 'gh', 'iw', 'ih', 'zx', 'zy')]
            need_reloading=number_of_tiles>anvil.maxNumberOfTiles or (gw, gh)!=(anvil.dimSpace[0], anvil.dimSpace[1])
            if need_reloading:
                if sg.popup_ok_cancel('This anvil has too many tiles or has the wrong dimensions ! We need to reload.', title='')=='cancel':
                    return False
            #if the current number of tiles is higher than the new number of tiles, we remove some of them.
            for i in range(number_of_tiles, anvil.numberOfTiles):
                self.remove_map(anvil)
            #we resize and translate the image
            anvil.box0=(zx, zy)
            anvil.dimBox=(iw, ih)
            anvil.image=np.array([[ FRACTAL_COLOR for i in range(anvil.dimBox[0]) ] for j in range(anvil.dimBox[1])], np.uint8)
            self.frac.images[anvil.name]=copy.copy(anvil.image)
            self.frac.originalImages[anvil.name]=copy.copy(anvil.image)
            #if we need to add maps we ad some tile positions and the corresponding childs to the fractal
            for i in range(anvil.maxNumberOfTiles,number_of_tiles):
                anvil.tilePositions.append( [[10*i+anvil.box0[0], 10*i+anvil.box0[1]],[10*i+anvil.box0[0]+anvil.dimBox[0], 10*i+anvil.box0[1]],[10*i+anvil.box0[0], 10*i+anvil.box0[1]+anvil.dimBox[1]]] )
                anvil.tilesChilds.append(anvil.name)
            for i in range(anvil.numberOfTiles, number_of_tiles):
                self.frac.addChild(anvil.name, f.Child(anvil.tilesChilds[i], f.Affine_transform.id()))
            #we adjust the number of tiles
            anvil.numberOfTiles=number_of_tiles
            anvil.maxNumberOfTiles=max(number_of_tiles, anvil.maxNumberOfTiles)
            #reload if needed, else just erase and redraw the tiles
            if need_reloading:
                anvil.dimSpace=(gw, gh)
                newin=self.reopenWindows()
            else:
                for tile in anvil.tiles:
                    tile.erase()
                for i in range(anvil.numberOfTiles):
                    self.win[anvil.name+str(i)+"text"].unhide_row()
                anvil.setTiles(self.win['graph_'+anvil.name])
                newin=self.win
            #loading the maps save from the m2 group we extracted before
            for i in range(number_of_tiles):
                anvil.tiles[i].modify_from_string(m2.group(r'map'+str(i)))
            self.frac.updateCurrentImage()
            return newin
    
    #now we define some sub-functions used in add_anvil and in load_forge.
    #the first asks the user a name and an input string.
    def input_anvil(self):
        name=sg.popup_get_text('This will require restarting the window. Choose a name for your anvil.')
        if name:
            taken=True
            while taken:
                taken=False
                for anvil in self.anvils:
                    if anvil.name==name:
                        name=sg.popup_get_text('This name is taken ! Choose another name')
                        taken=name
                    elif not anvil.regularName(name):
                        name=sg.popup_get_text(' Choose another name')
                        taken=name
        if not name:
            return False
        load_string=sg.popup_get_text('If you want to load a saved anvil, replace the text below by the save string', default_text=str(self.anvils[-1]))
        if not load_string:
            return False
        m=anvil.repattern.search(load_string)
        if not m:
            sg.popup('not a valid save string.')
            return False
        return (m,name, load_string)
    #then we construct the new anvil from the regex group
    def make_anvil(self, m, name):
        if not m:
            return False
        else:
            number_of_tiles=int(m.group('numtiles'))
            
            #preparing the maps data, if something goes wrong better if it happens now
            mapstrings=m.group("maps")
            
            repatternstring=""
            for i in range(number_of_tiles):
                repatternstring+=r"(?P<map"+str(i)+r">_\d*Mp0x_\d+_y_\d+_p1x_\d+_y_\d+_p2x_\d+_y_\d+)"
            mapsPattern=re.compile(repatternstring)
            m2=mapsPattern.search(mapstrings)
            if not m2:
                sg.Popup('Not a valid save string, probably missing some maps...')
                return False
            #getting the maps dimensions
            gw, gh, iw, ih, zx, zy=[int(string) for string in m.group('gw', 'gh', 'iw', 'ih', 'zx', 'zy')]
            newAnvil=Anvil(name,(gw, gh), (iw, ih), (zx, zy), numberOfTiles=number_of_tiles)
            self.anvils.append(newAnvil)
            return newAnvil

    def add_anvil(self):
        inputs=self.input_anvil()
        if not inputs:
            return self.win #in case we don't do anything, we return the original window
        m,name, load_string=inputs
        newAnvil=self.make_anvil( m, name)
        if not newAnvil:
            return self.win 
        newwin=self.reopenWindows()
        self.load_anvil(newAnvil, text=load_string)
        self.makeFractal()                    
        return newwin

    def remove_anvil(self, anvil):
        if len(self.anvils)==1:
            sg.popup('You cannot remove the last anvil.')
            return self.win
        #asking for confirmation
        result=sg.popup_ok_cancel('This operation is irreversible. We will need to reload the window.')
        if result=="Cancel":
            return self.win
        #first we remove the anvil's name from the tiles, so that it can be forgotten forever.
        for anvil2 in self.anvils:
            for i in range(anvil2.maxNumberOfTiles):
                if anvil2.tilesChilds[i]==anvil.name:
                    anvil2.tilesChilds[i]=anvil2.name
            for tile in anvil2.tiles:
                if tile.child==anvil.name:
                    tile.child=anvil2.name
        #then we remove the anvil from the anvil's list.
        self.anvils.remove(anvil)
        #and we reload
        newwin=self.reopenWindows()
        self.makeFractal()
        return newwin

    def __str__(self):  #contains the number of anvils and the string of the anvils, each preceded by the name of the anvil and followed by the list of the childs of the maps
        string="F_"+str(len(self.anvils))
        for anvil in self.anvils:
            string+='__'+anvil.name+"_"+str(anvil)
            for tile in anvil.tiles:
                string+="_"+tile.child
        return string

    def load_forge(self):
        name=sg.popup_get_text('Give your forge a name.')
        if not name:
            return self.win
        for anvil in self.anvils:
            s=re.search('^'+name+r'|^\d',anvil.name)
            if s:
                sg.popup('The name cannot be the same as the beggining as your anvils name.')
                return self.win
        if not self.anvils[0].regularName(name):
            return self.win
        #getting the forge string
        load_string=sg.popup_get_text('Copy the save string of the forge.')
        if (not load_string) or load_string=='Cancel':
            return self.win
        research=re.search('^F_(?P<nAnvils>\d+)(?P<anvils>.*)', load_string)
        if not research:
            sg.popup('Not a valid save string.')
            return self.win
        nAnvils=int(research.group('nAnvils'))
        anvilString=research.group('anvils')
        anvilsPattern=''
        for i in range(nAnvils):
            anvilsPattern+=r"__(?P<name"+str(i)+r">[^_]+)_"
            anvilsPattern+=r"(?P<anvil"+str(i)+r">An_\d+_gW_\d+_H_\d+"+\
                r"_iW_\d+_H_\d+_ZX_\d+_Y_\d+"+\
                r"(_\d*Mp0x_\d+_y_\d+_p1x_\d+_y_\d+_p2x_\d+_y_\d+)*)"
            anvilsPattern+=r"(?P<childs"+str(i)+r">(_[^_]+)*)"
        #anvilsPattern=r'__[^_]+_An_\d+_gW_\d+_H_\d+_iW_\d+_H_\d+_ZX_\d+_Y_\d+(_\d*Mp0x_\d+_y_\d+_p1x_\d+_y_\d+_p2x_\d+_y_\d+)*(_[_]+)*'
        anvilRe=re.search(anvilsPattern,anvilString)
        if not anvilRe:
            sg.popup('Not a valid Forge string !')
            print('string\n'+anvilString+'\n pattern \n'+anvilsPattern)
            print(anvilRe)

            return self.win
        anvilNames=[anvilRe.group('name'+str(i)) for i in range(nAnvils)]
        anvilPatterns=[self.anvils[0].repattern.search(anvilRe.group('anvil'+str(i))) for i in range(nAnvils)]
        childList=[anvilRe.group('childs'+str(i)) for i in range(nAnvils)]
        newAnvils=[]
        for i in range(nAnvils):
            newAnvil=self.make_anvil(anvilPatterns[i], name+anvilNames[i])
            if not newAnvil:
                sg.popup('Sorry nothing should have been wrong at this point. Trouble incoming.')
            newAnvils.append(newAnvil)
        newWin=self.reopenWindows()
        for i in range(len(newAnvils)):
            self.load_anvil(newAnvils[i], anvilRe.group('anvil'+str(i)))
            #modifying the childs
            childstring=childList[i]
            print(childList[i])
            childPattern=''
            tiles=newAnvils[i].tiles
            for j in range(len(tiles)):
                childPattern+=r'_(?P<child'+str(j)+r'>[^_]+)'
            mchild=re.search(childPattern, childstring)
            if not mchild:
                sg.popup('Issue with the number of childs...')
            else:
                for j in range(len(tiles)):
                    #tiles[j].child=mchild.group('child'+str(j))
                    self.win['origin_'+newAnvils[i].name+str(j)].update(name+mchild.group('child'+str(j)))
                    print(tiles[j].child)
        self.makeFractal()
        return newWin
            
                
            



        
        



#a series of methods to react to events.This only deals with events that never restart the window.
    def reactEvent(self,event, value):
        #reacting to events
        if event!="__TIMEOUT__":
            pass
        for anvil in self.anvils:
            if event=="zoomingActivation_"+anvil.name:
                zoomWindow(self.frac,anvil.name, float(value["multiplier_"+anvil.name]))
                self.frac.currentImageFamily=[f.Child(anvil.name, f.Affine_transform.id())]
                break
            if event=="save_"+anvil.name:
                string=str(anvil)
                sg.popup_get_text( default_text=string, message='Copy the following string:', size=(100, None))
            if event=="remove_map_but"+anvil.name:
                self.remove_map(anvil)
            for tileNumber in range(len(anvil.tiles)):
                if event=="edit_but"+anvil.name+str(tileNumber):
                    self.editingMap(anvil, tileNumber)
                if event=='rectify_but'+anvil.name+str(tileNumber):
                    tile=anvil.tiles[tileNumber]
                    for anvil2 in self.anvils:
                        if anvil2.name==tile.child:
                            width, height=anvil2.dimBox
                            break
                    tile.rectify(width, height)
        if event=="reset":
            self.resetImages()
        elif event=="iterate":
            self.frac.refineAllImages()
            self.update()
        elif event=='brighten':
            self.frac.brightenAllImages(cutoff=int(value["brighten_slider"]))
        elif event=="saveForge":
            sg.popup_get_text('Copy and save the following string', default_text=str(self))
        else:
            for anvil in self.anvils:
                if event=="graph_"+anvil.name:
                    self.mousePressed(anvil, value)
                    self.frac.brightenAllImages()
                elif event=="graph_"+anvil.name+"+UP":
                    self.mouseReleased(anvil, value)
        #updating the data 
        for anvil in self.anvils:
            for tileNumber in range(len(anvil.tiles)):
                self.updateFractalOrigin(anvil, tileNumber, value)
                self.updateFractalMap(anvil, tileNumber)  
        self.update()
        return False
        
    def mousePressed(self, anvil, value):
        i=0
        grasped=False
        for tile in anvil.tiles:
            if tile.grasped!=None:  #warning tile.grasped can be zero so if "tile.grasped:" instead of this line would cause bugs 
                grasped=True
                tile.mousePressed('graph_'+anvil.name, value)
                self.iterationsCounter=0
                self.win[anvil.name+str(i)+"text"].update("X"+str(i)+" Origin")
                break
            i+=1
        if not grasped:
            for tile in anvil.tiles:
                if tile.mousePressed('graph_'+anvil.name,value)!=None:  #warning mousepressed can return 0 so if tile.mousePressed(...): would cause bug
                    break
                
    def mouseReleased(self, anvil,value):
        i=0
        for tile in anvil.tiles:
            self.win[anvil.name+str(i)+"text"].update("_"+str(i)+" Origin")
            tile.mouseReleased()
            i+=1

    def editingMap(self, anvil, tileNumber):
        self.win['edit_but'+anvil.name+str(tileNumber)].update('Validate Edit')
        while True:
            event, value=self.win.read(timeout=0)
            if event in ('Exit', None):
                break
            if event=='edit_but'+anvil.name+str(tileNumber):
                string=value['input'+anvil.name+str(tileNumber)]
                if not anvil.tiles[tileNumber].modify_from_string(string):
                    sg.popup('Not a valid expression !')
                self.win['edit_but'+anvil.name+str(tileNumber)].update('Edit')
                break

    def resetImages(self):
        self.iterationsCounter=0
        for anvil in self.anvils:
            self.frac.images[anvil.name]=copy.copy(anvil.image)



def zoomWindow(fractal, imageName, sizeScaling):
    originalDimensions=fractal.images[imageName].shape[:2]
    imageDimensions=[int(sizeScaling*a) for a in originalDimensions]
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
        #first we deal with events that cannot reopen the window
        if event in ('Exit', None):
            break
        forge.reactEvent(event, value)
        #iterating the fractal 
        if forge.iterationsCounter<forge.maxIterations:
            forge.frac.refineAllImages()
            forge.iterationsCounter+=1
        if forge.brightenOn:
                forge.frac.brightenAllImages()
        #updating
        forge.frac.updateCurrentImage()
        forge.update()
        #then the events that may restart the window
        if event=="reopen":
            win=forge.reopenWindows()
        elif event=="add_anvil":
            win=forge.add_anvil()
        elif event=="loadForge":
            win=forge.load_forge()
        else:
            for anvil in forge.anvils:
                if event=="remove_"+anvil.name:
                    win=forge.remove_anvil(anvil)
                elif event=="add_map_but"+anvil.name:
                    win=forge.add_map(anvil)
                elif event=="load_"+anvil.name:
                    newin=forge.load_anvil(anvil)
                    if newin:
                      win=newin







if __name__ == '__main__':

    anvilWidth=550
    anvilHeight=450
    imageWidth=450
    imageHeight=350
    imageZero=[50,50]

    anvil2Width=400
    anvil2Height=400
    image2Width=275
    image2Height=275
    image2Zero=[50,50]

    winWidth=MONITOR_WIDTH-100
    winHeight=MONITOR_HEIGHT-100


    anvil=Anvil("A", (anvilWidth, anvilHeight), (imageWidth, imageHeight), imageZero, numberOfTiles=2)
    anvil2=Anvil("B", (anvil2Width, anvil2Height), (image2Width, image2Height), image2Zero, numberOfTiles=2)
    longAnvil=Anvil('C', (900,200), (800,100),[50,50], numberOfTiles=5)
    forge=Forge([anvil, anvil2],[winWidth,winHeight ])
    
    
    main_loop(forge)


# polysimilar_forge

This is an interface to construct fractal Iterated Functions Sets, with a "polysimilar" twist. Drag boxes, iterate functions, make ferns, dragons and fern-dragons ! 

It was submitted to the "Summer of Math Exposition" by 3blue1brown. If you just want the exposition and you don't want to use the interface, skip the "installation" part and just read the exposition bellow.

This version is up-to-date ! I won't merge this branch until the end of the SOME to allow for consistent reviewing.

# Installation

To use the interface, you need to have python with the libraries cv2 and pySimpleGUi. Download the two code files from the code directory of this git and save them in the same directory. You shall then compile the file "polysimilar_ui.py" with Python from this directory. For example, with Anaconda, set a terminal in the directory and do:

"anaconda path"/anaconda3/bin/python "directory path"/polysimilar_ui.py

 You can also execute the file it from an IDE but don't forget to set the console in the files's directory !
 If you want to modify the anvils, get more anvils and more maps, you have to edit the polysimilar_ui.py file, after the "" if __name__="__main__" "" at the end.
  
 # Exposition
 
 Let's zoom in on a fractal. I call it the "Griffin" :
 
<image src="https://media.giphy.com/media/ALfcY7Qb6QDiYwTeWV/giphy.gif?cid=790b761154f6f7cc183d66558d471ad4d79dff1232817e58&rid=giphy.gif&ct=g">

 Here is how the Griffin was forged:
 
<image src="https://media.giphy.com/media/6LQb5qjnHw2nGubKu8/giphy.gif?cid=790b76117b148c0bebc931958adfc366ab7ab59b706649f9&rid=giphy.gif&ct=g">
 
 But how does it work ? 
 The forge is a tool to make "Iterated Function Set" (IFS). Remember what happens when you put two mirrors in front of each other, or when you display your screen, on your screen.
 
 <img src="https://user-images.githubusercontent.com/74018582/130659601-c04179b1-b928-4d95-92ae-e12e5611558c.png" width=400>
 
 Iterated Function Sets are created the same way. The two boxes we dragged are the "mirror". They contain a copy of the full image (contained in the black box). At each passing millisecond, the full image is resised and copied in both of the two boxes. You can also see it step by step :
 
 <img src="https://media.giphy.com/media/qmFRS8eoejyBfbRasv/giphy.gif?cid=790b76116a5b4bb0b69bab7b00464cc26a83209284772d8a&rid=giphy.gif&ct=g">
 
 Here is another example : the fern (inspired by the "Barnsley fern"). 
 
<image src="https://media.giphy.com/media/uHv6vp8JPcQffhFSm8/giphy.gif?cid=790b761158a50e225dcfe853a89e0df4eb226af7352ca62e&rid=giphy.gif&ct=g">
 
 It disapears ! The reason for this fading is both mathematical and numerical.
 The numerical explication : when an image is resized, some black pixels are mixed with some purple pixels. This makes a slightly darker pixel. If it does not overlap with another darker pixel, this will get darker and darker, and fade to nothing.
  The mathematical explanation : the two boxes define two affine maps f and g. The IFS is defined as the set of limit points of sequences h1(h2(h3(h4(...(x0)...) for any initial point x0 and where the hi are either f and g. It is a subset of the plane. We could compute this subspace area... and in the case of the fern, the area is zero : if we could look at this set, we would see... nothing. Meanwhile, the Griffin has nonzero area, and does not fade. What we see just before the fern fades is close to what would see a mathematical entity capable of sensing infinitely small points.
 
Of course you don't want your fractal to disapear during the manipulation so I put an "anti-fading" effect which is activated when you drag the boxes. Anti-fading has the side-effect of making the fractal appear more "raw". If you want to refine your fractal, you can click on iterate a few times after you choose the boxes positions. You may then click on on of the boxe's edges to activate anti-fading and brighten the image.
 
 What about the "polysimilar" twist ? As 3Blue1Brown puts it, real-life fractals are "typically not self-similar". I wanted to forge fractals which are closer to real live. Here is an example, which I call the fern-dragon :
 
<image src="https://user-images.githubusercontent.com/74018582/130679580-b3f89875-f01f-408e-aa58-cec62409bf39.png" width=700>

 Under the fern image, two of the maps have for origin "B", and the first has for origin "A". This means that, at each iteration, instead of copying the image A in the two upper boxes, we copy the image of the fractal B ! The larger box still contains a copy of A.
 Saddly, the ferndragon is ultimately self-similar:
 
 <image src="https://media.giphy.com/media/5FHvJaiwdOY94Ri7Pl/giphy.gif?cid=790b76117b1cc036a1de4ef34d3153a0ec1df7929e714b56&rid=giphy.gif&ct=g">
 
 What if we set the origin of one of the B maps to be A ? We get the Fern-Shell :
 
 <image src="https://media.giphy.com/media/Pk9cWRA1ke1waf38c7/giphy.gif?cid=790b7611c410bb3968205c3fc0dc1473c429c09bcbf8b94a&rid=giphy.gif&ct=g">
 
 It's still kinda self-similar, but in a more complex way than usual IFS. I call this "polysimilar fractals". With enough images, we can probably forge lots of original fractals: bugs, spaceships, bugs driving spaceships.
 
 # The zooming issue.
 
 The infinite zoom uses the polysimilarity to construct arbitrarily precise images. When you zoom in, regular bumps happen when the next image is computed. You'll see that the zoom is not consistent if your fractal was touching the border of the image in the editor. This is very normal : the fractal is not a real polysimilar IFS if some part of the image is cut by the boundary.
 If you draged some of the lateral points of the boxes, you introduced some distortion : the function corresponding to the box is no more a similarity. At some point of the zoom, the image may become blurry.
 Another issue: if too many branches of the fractal overlap in your window, the zooming will become very slow.
 Finally, if one of the boxes in the forge is bigger than the image, the zooming code will fail to increase precision by decomposing the fractal in sub-parts, and the programm will crash by stack overflow. The smaller your boxes, the faster the zooming.
 
# Color
 
 When you iterate without the anti-fading, by clicking on the "iterate" button, the color changes. This is purely a consequence of the functions of OpenCV used in the code : when we glue an image, the function used is "bitwise or". This is a computationally efficient operation: the color of a pixel is composed of three 8-bit numbers (Blue, Green, Red in OpenCV, RGB in most other programms). When we do the "bitwise or" operation on two pixels of different colors (at the intersection of two boxes), the B, G and R values of the colors increase, and the resulting color is brighter.



 


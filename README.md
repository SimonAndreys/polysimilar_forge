# polysimilar_forge

This is an interface to construct fractal Iterated Functions Sets, with a "polysimilar" twist.

Drag boxes, iterate functions, make ferns, dragons and fern-dragons ! 
The interface displays "anvil". An anvil is an image, and several boxes. When you click "iterate", the image is copied in each of the boxes. As you iterate more, the image becomes a fractal !

![forge1](https://user-images.githubusercontent.com/74018582/130372176-0acf93aa-92d9-485c-8b33-0687472372df.png)

You can chose from which anvil comes the image copied in each boxes. For example, here the boxes 1 and 2 in the anvil A are carrying the image from the anvil B.

![forge2](https://user-images.githubusercontent.com/74018582/130372171-39b6f883-07da-45bd-8d10-ada6670f6365.png)

You can open a zooming window in which you zoom indefinitely on the fractal, revealing its self-similar nature. Well, sometimes the fractal is similar to another fractal, so let's call it "polysimilar".

To use the interface, you need to have python 3 with the libraries cv2 and pySimpleUi. Put the two code files in the same directory, and execute the file "polysimilar_ui.py" with Python from this directory. For example, with Anaconda, set a terminal in the directory and do:
<anaconda path>/anaconda3/bin/python <directory path>/polysimilar_ui.py

 You can also do it from an IDE but don't forget to set the console in the files's directory !
 If you want to modify the anvils, get more anvils and more maps, you have to edit the polysimilar_ui.py file, after the "if __name__="__main__" at the end.
  
 


# plotVR - Walk Through your Data in Cardboard VR

This is a prototype to get your data into a Google Cardboard and navigate using the computer keyboard.

Install the R-package:
```bash
devtools::install_github('thomann/plotVR',subdir='plotVR')
```
Then in R load and plot the first three dimensions of `iris` with `iris$Species` as color:
```r
library(plotVR)
plotVR(iris[,1:3],iris$Species)
```
When you load the library, it will start a server listening on port 2908
(you might have to allow the port to be opened in your firewall)
and then you have to direct your cardboard-smartphone to the corresponding address.
```
http://<ip-address of the machine running your R>:2908/plotVR.html
```
This will look something like:

![VR view](screen-vr.png?raw=true "VR view")

> Naturally, you also can visit the server page on your computer: <http://localhost:2908/plotVR.html>.

Tap on the screen to bring it to full-screen!

If you have a QR-reader installed on your device, you can get that quickly with:
```r
showQR()
```
Then scan it with your smartphone and open the link with the browser.

Once your device connects to the R session on your computer there will open a small window like the following:

![Continue button](screen-tk.png?raw=true "Continue button")

This window also will get the keyboard focus when it opens. You now can use your computer keyboard to navigate through the virtual space (like in Quake!):

|  Key  |  Movement |
|-------|-----------|
|   w   |  forward  |
|   s   | backward  |
|   a   |    left   |
|   d   |   right   |
|   q   |     up    |
|   e   |   down    |
|   up/down-arrow   |   rotate vertically    |
|  left/right-arrow |   rotate horizontally  |
| space |  toggle velocity |
|   r   |  reload   |

Now if you plot something new it will be reloaded in your cardboard:
```r
plotVR(trees)
```

## Issues

* This is not very stable at the moment!
* On Windows: the TK-control window is shown but does not react, so the keyboard feature is broken.
* There need to be better keyboard assignments, and maybe some more interface in the keyboard focus window.
* The default values are not well set, e.g. the starting point of the virtual observer.
* There is an Android App on the way for better on-device handling and performance.
* The files `plotVR.m` and `python.ipynb` can be used in MATLAB and Python, resp. however
  For that a server has to be started `./startServer.sh` and this just starts the R-version.

## Acknowledgements

* <http://threejs.org> for the WebGL-version
* `httpuv` for the websocket-server implementation
* `tcltk` for the focus grabbing window
* <https://vr.google.com/cardboard/> for the cardboard!

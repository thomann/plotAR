# plotVR - Walk Through Your Data

This is a prototype to get your data into a Google Cardboard (VR) or into Augmented Reality (AR) and navigate using the computer keyboard.

> This package was presented at EuroPython 2019.
> Check out the recording video on <https://youtu.be/lxXC76jHc98?t=5h20m>. *The video covers the whole day in that room - the talk starts at 5h20m and ends at 5h46m.*

Are you bored by 3D-plots that only give you a simple rotatable 2d-projection? plotVR provides a simple way for data scientists to plot data, pick up a phone, get a real 3d impression - either by VR or by AR - and use the computer's keyboard to walk through the scatter plot (see [live demo](https://thomann.github.io/plotVR/plotVR/inst/)):

![Overview](images/overview.png?raw=true "Overview")

The technologies beneath this project are: a web server that handles the communication between the DataScience-session and the phone, WebSockets to quickly proxy the keyboard events, QR-codes facilitate the simple pairing of both, and an HTML-Page on the computer to grab the keyboard events. And the translation of these keyboard events into 3D terms is a nice exercise in three.js, OpenGL, and SceneKit for HTML, Android, and iOS resp.

> **Warning:** All data is transmitted unencrypted and everybody can connect! Please be carefule with private data!

> **Disclaimer:** This package is provided as-is and every usage is on your own ris.

## Installation

Install the R-package:
```r
devtools::install_github('thomann/plotVR',subdir='plotVR-R')
```
or the Python package:
```bash
pip install --upgrade "git+https://github.com/thomann/plotVR#egg=plotvr&subdirectory=plotVR-py"
```
> The installation from sources currently needs symbolic links to work, which is a bit of an issue on windows (see below). If you cannot make it work, wait to obtain precompiled wheels.

Also check out the native mobile apps:
- iOS: <https://github.com/thomann/PlotAR-ios>
- Android: <https://github.com/thomann/plotVR-android>


## Quick Tour

Working with the package is meant to be seamless - but it is a little hard to explain in text. Please check out the above [video](https://youtu.be/lxXC76jHc98?t=5h27m) at 5h27m where the demo starts.

Here we will describe how to plot the data in RStudio or Jupyter, then view it on your device, and finally navigate through the scene.

### Plot your data

In R load and plot the first three dimensions of `iris` with `iris$Species` as color:
```r
library(plotVR)
startExternalServerProcess()
plotVR(iris[,1:3],iris$Species)
```
In Python - or better even in Jupyter Lab - enter the following:
```python
import plotvr
plotvr.start_server_process()
from sklearn import datasets
iris = datasets.load_iris()
plotvr.plotvr(iris.data, iris.target)
```
This will look something like
![RStudio](images/screen-rstudio.png?raw=true)
and
<center><img src="images/screen-jupyter.png?raw=true" width=250></center>

### View in a browser or on a device

Now you can open the advertised webpage - also on your mobile device using any QR-code reader:
```
http://<ip-address of your machine>:2908/index.html
```
This will look something like (see [live demo](https://thomann.github.io/plotVR/plotVR/inst/)):

![VR view](images/screen-vr.png?raw=true "VR view")

> Naturally, you also can visit the server page on your computer: <http://localhost:2908/plotVR.html>.

Tap on the screen to bring it to full-screen!

### Keyboard Navigation

Now in order to navigate through your scene you can use the keyboard. In order to capture key events click on the display keyboard:
![Keyboard](images/screen-keyboard.png?raw=true)

They keyboard warns if it loses focus:
![Keyboard without focus](images/screen-keyboard-nofocus.png?raw=true)

This window also will get the keyboard focus when it opens. You now can use your computer keyboard to navigate through the virtual space (like in Quake!):

|  Key              |  Movement             |
|-------------------|-----------------------|
|   w               |  forward              |
|   s               | backward              |
|   a               |    left               |
|   d               |   right               |
|   q               |     up                |
|   e               |   down                |
|  up/down-arrow    |  rotate vertically    |
|  left/right-arrow |  rotate horizontally  |
|   r               |  reload               |
|  space            |  toggle velocity      |

### 

Now if you plot something new it should be reloaded automatically in your viewer:
```r
plotVR(trees)
```

## Issues

* This is not very stable at the moment!
* This repo uses symlinks which for Windows explicitely need to be activated, see <https://github.com/git-for-windows/git/wiki/Symbolic-Links>.
* There need to be better keyboard assignments, and maybe some more interface in the keyboard focus window.
* The default values are not well set, e.g. the starting point of the virtual observer.
* The file `plotVR-matlab/plotVR.m` can be used in MATLAB if you have access to a running server in Python or R.

## Acknowledgements

* For the WebVR-client: [`three.js`](http://threejs.org),
  [`polyfill`](https://github.com/googlevr/webvr-polyfill), and
  [`webvr-boilerplate`](https://github.com/borismus/webvr-boilerplate)
  (all needed parts included in this repository under `plotVR/inst/js/third-party`)
* [`httpuv`](https://github.com/rstudio/httpuv) for the websocket-server implementation in R
* [`tornado`](https://www.tornadoweb.org/) for the websocket-server implementation in Python
* <https://vr.google.com/cardboard/> for the cardboard!

# plotVR - Architecture and protocols

For an active plotVR session there are three realms: 

* The data source from which you want to visualize some data:
  -  Currently an R/Python/MATLAB-session
* The VR-device, for which there are two independent implementations:
  - WebVR: included in the R-package, works in any Browser, both on
    Android/iOS and on the desktop.
  - Android: separate app, which performs better, also can save different links
    to servers etc.
* A server that connects both endpoints
  - At the moment this runs in R.
  - Opens a GUI (TK) that can control the viewer like in games.
  - Usually runs on the same machine as the data source.
  - It is a web server that serves `data.json` and the WebVR version via GET,
    can receive new `data.json` via POST requests, and
     is listening for WebSocket connections.
    

The data source writes as POST a model to the server (JSON).
VR-devices open a WebSocket connection to the server and if
new data is available they download it via a simple GET from the server.
Currently the server only has one model.

The data source communicates with the server and that again with the VR-device:
```
data source 1 ----> server -----> VR-device 1
                 /          \
data source 2 ---            ---> VR-device 2
```
The usual setup actually looks like this
```
[ data source ----> server ]   ----->   VR-device
```
Therefore the critical communication is between the server and the VR-device and
can lead to problems, e.g. if the endpoints are on different networks.

Eventually there might also be a communication from the server to the data source
e.g. to get the location of the virtual avatar,
maybe even from the VR-device to the server.

## Model: `data.json`

A JSON file:
```json
{ "data": [
    [-0.897673879196766,1.01560199071363,-1.33575163424152,1],
    [-1.13920048346495,-0.13153881205026,-1.33575163424152,1],
    [-1.38072708773314,0.327317509055298,-1.39239928624498,1],
    ....,
    [0.0684325378759866,-0.13153881205026,0.760211489886395,3 ]
  ],
  "speed":  0 
}
```
This consists of
- a `data` property which is a $n\times 4$ matrix of 3 spatial coordinates and a color index
- `speed` the speed at which the avatar should fly (deprecated?)


## Controller-Protocol: WebSocket

The communication from the server to the VR-device are quite simple commands:

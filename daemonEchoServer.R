library(httpuv)

.lastMessage <- NULL

app <- list(
  call = function(req) {
    cat('serving ',req$PATH_INFO, '\n')
    wsUrl = paste(sep='',
                  '"',
                  "ws://",
                  ifelse(is.null(req$HTTP_HOST), req$SERVER_NAME, req$HTTP_HOST),
                  '"')

    list(
      status = 200L,
      headers = list(
        'Content-Type' = 'text/html'
      ),
      body = paste(
        sep = "\r\n",
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '<style type="text/css">',
        'body { font-family: Helvetica; }',
        'pre { margin: 0 }',
        '</style>',
        "<script>",
        sprintf("var ws = new WebSocket(%s);", wsUrl),
        "ws.onmessage = function(msg) {",
        '  var msgDiv = document.createElement("pre");',
        '  msgDiv.innerHTML = msg.data.replace(/&/g, "&amp;").replace(/\\</g, "&lt;");',
        '  document.getElementById("output").appendChild(msgDiv);',
        "}",
        "function sendInput() {",
        "  var input = document.getElementById('input');",
        "  ws.send(input.value);",
        "  input.value = '';",
        "}",
        "</script>",
        "</head>",
        "<body>",
        '<h3>Send Message</h3>',
        '<form action="" onsubmit="sendInput(); return false">',
        '<input type="text" id="input"/>',
        '<h3>Received</h3>',
        '<div id="output"/>',
        '</form>',
        "</body>",
        "</html>"
      )
    )
  },
  onWSOpen = function(ws) {
    cat('open ws: ',ws$.handle,'\n')
    all_ws <<- c(all_ws, list(ws))
    ws$onMessage(function(binary, message) {
      .lastMessage <<- message
      ws$send(message)
    })
    ws$onClose(function(){
      cat('got WS close\n')
      handles <- sapply(all_ws, function(x) x$.handle)
      all_ws <- all_ws[handles != ws$.handle]
    })
  }
)
all_ws <- list()

server <- startDaemonizedServer("0.0.0.0", 2908, app)

tcltk::tktoplevel()
# label.widget <- tklabel(tt, text = "Hello, World!")
# button.widget <- tkbutton(tt, text = "Push",
#                           command = function()cat("OW!\n"))
# tkpack(label.widget, button.widget) # geometry manager

# check the value of .lastMessage after echoing to check it is being updated

# call this after done
#stopDaemonizedServer(server)

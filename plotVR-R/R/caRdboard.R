
# the state of the controller:
pkg.env <- new.env()

# list of all connected clients
pkg.env$clients <- list()

# the handle of the httpuv-server daemon
pkg.env$server_handle <- NULL

# the model to serve to devices
pkg.env$vr_data_json <- NULL

# interval for blocking server to serve at once
pkg.env$interruptIntervalMs <- 250

log.info <- function(...){
  try({
    if(getOption("plotVR.log.info", default=TRUE))
      cat(format(Sys.time(), "[%Y-%m-%d %H:%M:%S]"), "plotVR info:",...,fill=T)
  })
  try({
    filename <- getOption("plotVR.log.info.file")
    if(!is.null(filename))
      cat("plotVR info:",...,fill=T,file=filename)
  })
}

# ' @importFrom datasets iris
defaultDataJson <- function()
  plotVR(datasets::iris[,1:3],col=datasets::iris$Species, name="Iris", .send=FALSE, doOpenController=F)


process_request <- function(req, base="~/density/vr/") {
  log.info("Serving",req$PATH_INFO)
  # print(ls.str(req))
  log.info(req$REQUEST_METHOD)
  if(req$REQUEST_METHOD=="POST"){
    return(handle_upload_data(req))
  }
  path <- req$PATH_INFO
  wsUrl = paste0('ws://', ifelse(is.null(req$HTTP_HOST), req$SERVER_NAME, req$HTTP_HOST),'/ws')
  if(path=="/") path <- "/index.html"
  if(path=="/plotVR.html") path <- "/index.html"
  if( path == '/echo' )
    return(handle_echo(wsUrl))
  if(path == "/qr.json"){
    url <- getUrl()
    qr <- getQRCode(url)
    qr_json <- jsonlite::toJSON(list(qr=qr, url=url), auto_unbox=TRUE)
    return(list(status = 200L,
                headers = list('Content-Type' = 'application/json'),
                body = qr_json ))
  }else if(path == "/data.json"){
    if(is.null(pkg.env$vr_data_json))
      pkg.env$vr_data_json <- defaultDataJson()
    return(list(status = 200L,
                headers = list('Content-Type' = 'application/json'),
                body = pkg.env$vr_data_json ))
  }else{
    real_filename <- system.file(path,package="plotVR")
    real_filename <- sub("../","", real_filename,fixed=T)
    log.info(" changed to ",real_filename)

    if(!file.exists(real_filename)){
      log.info("Does not exist!!")
      return(list(status=404L,headers=list('Content-Type'="text/plain"),body="Nothing here."))
    }
    content_type <- 'text/html'
    if(tools::file_ext(path)=="png") content_type <- "image/png"
    if(tools::file_ext(path)=="js") content_type <- "application/javascript"
    return(list(status = 200L,
                headers = list('Content-Type' = content_type),
                body = list(file=real_filename)))
  }
}

handle_upload_data <- function(req){
  log.info('Got POST Content-type;', req$CONTENT_TYPE)
  input_str <- req$rook.input$read_lines()
  json_data <- paste(input_str, collapse="\n")
  pkg.env$vr_data_json <- json_data
  log.info('Having new data from POST -- nchar:',paste0(nchar(json_data),collapse=','),'data:',json_data)
  #ws()log.info(pkg.env$vr_data_json,fill=T)

  broadcastRefresh()

  log.info('got data and broadcasted refresh')
  return(list(status = 200L,
              headers = list('Content-Type' = 'text/plain'),
              body = "OK"))
}

handle_echo <- function(wsUrl){
  list(status = 200L,
                headers = list('Content-Type' = 'text/html'),
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
}


processWS <- function(thesock) {
  log.info("got WebSocket")
  self <- as.environment(list(ws=thesock, isDevice=F, isController=F, hasFocus=F))
  pkg.env$clients <- c(pkg.env$clients, list(self))
  thesock$onMessage(function(binary, message) onMessage(binary, message, self))
  thesock$onClose(function() onClose(self) )
}

onMessage <- function(binary, message, self) {
    log.info("got WS message",message)
    body <- jsonlite::fromJSON(message)
    keys <- ls(body)
    if('shutdown' %in% keys){
      # FIXME broadcast it?
      stopBlockingServer()
      return()
    }
    sendStatus <- F
    if('focus' %in% keys){
      self$hasFocus <- body$focus
      sendStatus <- T
    }
    if('controller' %in% keys){
      self$isController <- body$controller
      sendStatus <- T
    }
    if('device' %in% keys){
      self$isDevice <- body$device
      sendStatus <- T
    }
    if(sendStatus){
      broadcastStatus()
    }else{
      broadcast(message)
    }
  }

onClose <- function(self){
  handle <- self$thesock$.handle
  log.info("Closing websocket: ",handle)
  # str(thesock)
  # remove that client from all_clients
  handles <- sapply(pkg.env$clients, function(x) x$thesock$.handle)
  pkg.env$all_clients <- pkg.env$all_clients[handles != handle]
  log.info("Closed websocket: ",handle)
}

app <- list(call=process_request, onWSOpen = processWS)

#' Start the WebServer in a blocking version.
#'
#' This blocks until interrupted or killed. This is the actual server
#' that gets run by \code{\link{startServer}} in a background process.
#'
#' @param host on which host to listen
#' @param port on which port to listen
#' @param interruptIntervalMs passed to \code{httpuv}
#'
#' @export
startBlockingServer <- function(host="0.0.0.0", port=2908, interruptIntervalMs=ifelse(interactive(), 100, 1000)){

  log.info("Welcome to the PlotVR Server")
  server <- httpuv::startServer(host, port, app)
  pkg.env$server_handle <- server

  on.exit(stopBlockingServer())
  pkg.env$stopped <- FALSE
  pkg.env$interruptIntervalMs <- interruptIntervalMs

  cat('Now do: browseURL("http://',host,':',port,'/")\n')

  while (!pkg.env$stopped) {
    httpuv::service(interruptIntervalMs)
    Sys.sleep(0.001)
  }

  log.info("Stopped blocking server")
}


stopBlockingServer <- function(server=pkg.env$server_handle){
  if(is.null(server))
    return()
  log.info("Stopping Blocking Server ",pkg.env$server_handle,"... ")

  if(server == pkg.env$server_handle){
    pkg.env$server_handle <- NULL

    # set stopped flag and give time
    pkg.env$stopped <- TRUE
    Sys.sleep(2*pkg.env$interruptIntervalMs/1000)
    log.info("waited", 2*pkg.env$interruptIntervalMs/1000, 's')
  }

  try(httpuv::stopServer(server))

  log.info("succeeded\n")
}

broadcastRefresh <- function(data){
  if(!missing(data)){
    pkg.env$vr_data_json <- data
  }
  broadcast(list(key='reload_data'))
}

broadcastStatus <- function(data){
  print(length(pkg.env$clients))
  status <- list(
    numDevices=sum(sapply(pkg.env$clients, `[[`, 'isDevice')),
    numControllers=sum(sapply(pkg.env$clients, `[[`, 'isController')),
    numFocus=sum(sapply(pkg.env$clients, `[[`, 'hasFocus'))
  )
  broadcast(list(status=status))
}

broadcast <- function(message){
  if(!is.character(message))
    message <- jsonlite::toJSON(message, auto_unbox=TRUE, pretty=TRUE)
  for(client in pkg.env$clients){
    log.info("Sending", message, "to") #,as.character(ws))
    try(client$ws$send(message))
  }
}

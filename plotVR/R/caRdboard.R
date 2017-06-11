
# the state of the controller:
pkg.env <- new.env()
# list of all connected clients
pkg.env$all_clients <- list()
# the handle of the httpuv-server daemon
pkg.env$server_handle <- NULL
# the model to serve to devices
pkg.env$vr_data_json <- NULL
# the global keyboard of the controller
pkg.env$keyboard <- NULL
# indicates whether the server 'blocking' or 'daemon' (or 'none')
pkg.env$server.type <- 'none'
# indicates whether the server was stopped (used for the blocking server)
pkg.env$stopped <- FALSE
# interval for blocking server to serve at once
pkg.env$interruptIntervalMs <- 250

# list of controllers
pkg.env$controller <- list()
# list of focus
pkg.env$focus <- list()

log.info <- function(...){
  try({
    if(getOption("plotVR.log.info", default=FALSE))
      cat(format(Sys.time(), "[%Y-%m-%d %H:%M:%S]"), "plotVR info:",...,fill=T)
  })
  try({
    filename <- getOption("plotVR.log.info.file")
    if(!is.null(filename))
      cat("plotVR info:",...,fill=T,file=filename)
  })
}


process_request <- function(req, base="~/density/vr/") {
  log.info("Serving",req$PATH_INFO)
  # print(ls.str(req))
  if(req$REQUEST_METHOD=="POST"){
    log.info('Got POST Content-type;',req$CONTENT_TYPE)
    #print(ls.str(req))
    input_str <- req$rook.input$read_lines()
    input_str <- paste(input_str, collapse="\n")
    if(substring(input_str,0,5)=="data=")
      input_str <- URLdecode(substring(input_str,6))
    if(req$QUERY_STRING == "?add=TRUE"){
      warning('Adding not yet implemented')
    }else{
      pkg.env$vr_data_json <- input_str
    }
    log.info('Having new data from POST -- nchar:',paste0(nchar(input_str),collapse=','),'data:',input_str)
    #ws()log.info(pkg.env$vr_data_json,fill=T)
    broadcastRefresh()
    log.info('got data and broadcasted refresh')
    return(list(status = 200L,
                headers = list('Content-Type' = 'text/plain'),
                body = "OK"))
  }
  path <- req$PATH_INFO
  wsUrl = paste0('"ws://', ifelse(is.null(req$HTTP_HOST), req$SERVER_NAME, req$HTTP_HOST),'"')
  if(path=="/") path <- "/index.html"
  if(path=="/plotVR.html") path <- "/index.html"
  if( path == '/echo' ){
    return(list(status = 200L,
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
    ))
  }else if(path == "/qr.json"){
    url <- getUrl()
    qr <- qrcode::qrcode_gen(url, dataOutput=TRUE, plotQRcode=FALSE)
    data_frag <- paste(apply(qr,1,paste, collapse=','),collapse="],\n[")
    qr_json <- paste('{ qr: [[ ',data_frag,']]\n}\n')
    return(list(status = 200L,
                headers = list('Content-Type' = 'application/json'),
                body = qr_json ))
  }else if(path == "/data.json"){
    if(is.null(pkg.env$vr_data_json))
      pkg.env$vr_data_json <- writeData(iris[,1:3],col=iris$Species,loc=NULL)
    return(list(status = 200L,
                headers = list('Content-Type' = 'application/json'),
                body = pkg.env$vr_data_json ))
  }else{
    if(substring(path,2,2)=="_"){
      real_filename <- substring(path,3)
    }else{
      real_filename <- system.file(path,package="plotVR")
    }
    real_filename <- sub("../","", real_filename,fixed=T)
    log.info(" changed to ",real_filename)

    if(!file.exists(real_filename)){
      log.info("Does not exist!!")
      return(list(status=404L,headers=list('Content-Type'="text/plain"),body="Nothing here."))
    }
    content_type <- 'text/html'
    if(tools::file_ext(path)=="png") content_type <- "image/png"
    return(list(status = 200L,
                headers = list('Content-Type' = content_type),
                body = list(file=real_filename)))
  }
}


processWS <- function(thesock) {
  log.info("got WebSocket")
  tt_handle <- if(getOption('plotVR.keyboard.individual',default=FALSE))
    tk_keyboard(thesock$send, wait=F, closeSock=thesock$close)
  else
    NULL
  pkg.env$all_clients <- c(pkg.env$all_clients, list(thesock) )
  setNumberDevices(length(pkg.env$all_clients))
  #str(pkg.env$all_clients)
  thesock$onMessage(function(binary, message) {
    log.info("got WS message",message)
    if(message=="close"){
      onClose(thesock, tt_handle)
    }else if(message == "shutdown"){
      # FIXME broadcast it?
      stopServer()
    }else if(startsWith(message, prefix="broadcast key ")){
      key <- substring(message, nchar("broadcast key ")+1)
      broadcastDevices(key)
    }else if(message == "controller: 1"){
      pkg.env$controller[[thesock$.handle]] <- 1
    }else if(message == "focus: 1"){
      pkg.env$focus[[thesock$.handle]] <- 1
    }else if(message == "focus: 0"){
      pkg.env$focus[[thesock$.handle]] <- 0
    }else{
      thesock$send(paste0('got message: ',message))
    }
  })
  thesock$onClose(function(){
    log.info("got WS close")
    onClose(thesock, tt_handle)
  })
}

onClose <- function(thesock, tt_handle){
  handle <- thesock$.handle
  log.info("Closing websocket: ",handle)
  # str(thesock)
  # remove that client from all_clients
  handles <- sapply(pkg.env$all_clients, function(x) x$.handle)
  pkg.env$all_clients <- pkg.env$all_clients[handles != handle]
  setNumberDevices(length(pkg.env$all_clients))
  # close keyboard for that client
  if(!is.null(tt_handle))
    tkdestroy(tt_handle)
  if(handle %in% pkg.env$controller)
    pkg.env[[controller]] <- -1
  if(handle %in% pkg.env$focus)
    pkg.env[[focus]] <- -1
  log.info("Closed websocket: ",handle)
}

easyWS <- function(ws) {
  try({
    log.info('open easy ws: ',ws$.handle)
    pkg.env$all_clients <- c(pkg.env$all_clients, list(ws))
    ws$onMessage(function(binary, message) {
      log.info('easy ws ',ws$.handle,'message: ',message,'\n')
      .lastMessage <<- message
      ws$send(message)
    })
  })
}

app <- list(call=process_request, onWSOpen = processWS)
# app <- list(call=process_request, onWSOpen = easyWS)

startGlobalKeyboard <- function(){
  # if(!getOption('plotVR.keyboard.individual',default=FALSE))
  #   pkg.env$keyboard <- tk_keyboard(broadcastDevices, wait=F, closeSock=function(){}, link=getUrl())
}

#' Open Keyboard (in the viewer pane if in RStudio).
#' @export
openKeyboard <- function(){
  viewer <- getOption("viewer")
  if(is.null(viewer))
    viewer <- utils::browseURL
  viewer(paste0(getUrl(), 'keyboard.html'))
}

#' Start the WebServer in a blocking version.
#' @export
startBlockingServer <- function(host="0.0.0.0", port=2908, interruptIntervalMs=ifelse(interactive(), 100, 1000)){

  startGlobalKeyboard()

  server <- httpuv::startServer(host, port, app)
  pkg.env$server_handle <- server
  pkg.env$server.type <- 'blocking'

  on.exit(stopBlockingServer())
  pkg.env$stopped <- FALSE
  pkg.env$interruptIntervalMs <- interruptIntervalMs

  cat('Now do: browseURL("http://",host,":",port,"/")\n')

  while (!pkg.env$stopped) {
    httpuv::service(interruptIntervalMs)
    Sys.sleep(0.001)
  }

  log.info("Stopped blocking server")
}

#' @export
#' @import httpuv
startDaemonServer <- function(){
  pkg.env$server_handle <- httpuv::startDaemonizedServer("0.0.0.0", 2908, app)
  pkg.env$server.type <- 'daemon'
  cat("Started Daemon server: ",pkg.env$server_handle,"\n")
  startGlobalKeyboard()
  invisible(pkg.env$server_handle)
}

#' @export
stopServer <- function(){
  if(pkg.env$server.type == 'blocking'){
    stopBlockingServer()
  }else if(pkg.env$server.type == 'daemon'){
    stopDaemonServer()
  }else{
    warning('stopping unknown server', pkg.env$server.type)
  }
}

#' @export
stopBlockingServer <- function(server=pkg.env$server_handle){
  if(is.null(server))
    return()
  log.info("Stopping Blocking Server ",pkg.env$server_handle,"... ")

  if(server == pkg.env$server_handle){
    pkg.env$server_handle <- NULL
    pkg.env$server.type <- 'none'

    # set stopped flag and give time
    pkg.env$stopped <- TRUE
    Sys.sleep(2*pkg.env$interruptIntervalMs/1000)
    log.info("waited", 2*pkg.env$interruptIntervalMs/1000, 's')
  }

  try(httpuv::stopServer(server))

  if(!is.null(pkg.env$keyboard)){
    tkdestroy(pkg.env$keyboard)
    pkg.env$keyboard <- NULL
  }
  # FIXME remove on.exit() handler??
  log.info("succeeded\n")
}

#' @export
stopDaemonServer <- function(){
  if(is.null(pkg.env$server_handle))
    return()
  log.info("Stopping Daemon Server ",pkg.env$server_handle,"... ")
  try(httpuv::stopDaemonizedServer(pkg.env$server_handle))
  pkg.env$server_handle <- NULL

  if(!is.null(pkg.env$keyboard)){
    tkdestroy(pkg.env$keyboard)
    pkg.env$keyboard <- null
  }
  log.info("succeeded\n")
}

setNumberDevices <- function(num){
  # tclvalue(pkg.env$connectedText) <- num
  broadcastDevices(paste0('number devices: ',num))
}

broadcastRefresh <- function(data){
  if(!missing(data)){
    pkg.env$vr_data_json <- data
  }
  broadcastDevices("reload_data")
}

broadcastDevices <- function(message){
  # lazy start Server
  if(is.null(pkg.env$server_handle))
    startDaemonServer()
  log.info('Broadcasting:',message)
  for(ws in pkg.env$all_clients){
    log.info("Sending", message, "to") #,as.character(ws))
    try(ws$send(message))
  }
}

.onAttach <- function(libname, pkgname){
  # if(interactive() && getOption('plotVR.startOnAttach', default=FALSE))
    # startDaemonServer()
}


.onDetach <- function(libpath){
  log.info("Detaching!!!\n")
  stopDaemonServer()
}
.onUnload <- function(libpath){
  log.info("Unloading!!!\n")
  stopDaemonServer()
}


#' @export
.Last.lib <- function(libpath){
  log.info("Detaching or Unloading via .Last.lib!!!\n")
  stopTheDaemonServer()
}

restartDaemonServer <- function(){
  stopDaemonServer()
  startDaemonServer()
}

getIP <- function(){
  os <- Sys.info()[['sysname']]
  if(os=='Windows'){
    # ???
    tmp <- system('ipconfig',intern=T)
    res <- gsub(".*?: ([0-9.]+)[^0-9.]*", "\\1", tmp[grep('IPv4',tmp)])
    res <- res[nchar(res)>0]
    if(is.null(res)){
      warning('No IP-addresses were found, using localhost ip address')
      return('127.0.0.1')
    }
    if(length(res)>1)
      warning('More than one IP-address was found, using the first one: ',res[1], 'others: ', paste(res[-1],collapse=', '))
    res[1]
  }else if(os=='Darwin'){
    suppressWarnings(
      ret <- system("route -n get default 2>/dev/null |grep interface|sed 's/^.*: //' | xargs ifconfig | grep 'inet ' | sed 's/.*inet \\([0-9.]*\\) .*/\\1/'", intern=TRUE)
    )
    if(length(ret)==0 || nchar(ret)==0)
      ret <- '127.0.0.1'
    ret
  }else if(os=='Linux'){
    strsplit(system('hostname -I',intern=TRUE)," ")[[1]][1]
  }else{
    # ???
    warning('Did not recognize os, using localhost ip address')
    '127.0.0.1'
  }
}
getHostInfo <- function(hostname=R.utils::System$getHostname()){
  out <- system(paste('host',hostname),intern=TRUE)
  out <- out[grep('has address',out)]
  strsplit(out, " has address ")
}

getUrl <- function(host=NULL,port=2908,useIP=TRUE,useFullName=FALSE) {
  if(useIP){
    host <- getIP()
  }else if(useFullName){
    if(is.null(host)){
      if(requireNamespace('R.utils', quietly=TRUE)){
        host <- R.utils::System$getHostname()
        info <- getHostInfo(host)
        if(length(info)>=1)
          host <- info[[1]][1]
      }else{
        warning('no host provided and package R.utils not installed, therefore using localhost')
        host <- 'localhost'
      }
    }else{
      warning('did not find out host, using localhost')
      host <- 'localhost'
    }
  }
  # FIXME is this needed?
  # url <- paste0("http://",host,":",port,"/plotVR.html")
  url <- paste0("http://",host,":",port,"/")
  return(url)
}

#' @export
showQR <- function(...){
  require(qrcode)

  url <- getUrl(...)
  # viewer <- getOption('viewer')
  # viewer()
  qrcode::qrcode_gen(url)
  invisible(url)
}

#' @export
openViewer <- function(...){
  url <- getUrl(...)
  viewer <- getOption('viewer')
  viewer(url)

  invisible(url)
}

#' @export
openController <- function(...){
  url <- paste0(getUrl(...),'keyboard.html')
  viewer <- getOption('viewer')
  viewer(url)

  invisible(url)
}

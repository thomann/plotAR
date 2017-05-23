pkg.env <- new.env()

pkg.env$all_clients <- list()


process_request <- function(req, base="~/density/vr/") {
  cat("Serving ",req$PATH_INFO, "\n")
  if(req$REQUEST_METHOD=="POST"){
    cat('Got POST Content-type; ',req$CONTENT_TYPE, fill=T)
    #print(ls.str(req))
    input_str <- req$rook.input$read_lines()
    if(substring(input_str,0,5)=="data=")
      input_str <- URLdecode(substring(input_str,6))
    pkg.env$vr_data_json <- input_str
    #ws()cat(pkg.env$vr_data_json,fill=T)
    broadcastRefresh()
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
  }else if(path == "/data.json"){
    if(is.null(pkg.env$vr_data_json))
      pkg.env$vr_data_json <- writeData(iris[,1:3],col=iris$Species,loc=NULL)
    return(list(status = 200L,
                headers = list('Content-Type' = 'application/json'),
                body = pkg.env$vr_data_json ))
  }else{
    cat("Trying: ",path)
    if(substring(path,2,2)=="_"){
      real_filename <- substring(path,3)
    }else{
      real_filename <- system.file(path,package="plotVR")
    }
    real_filename <- sub("../","", real_filename,fixed=T)
    cat(" changed to ",real_filename,"\n")

    if(!file.exists(real_filename)){
      cat("Does not exist!!\n")
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
  cat("got WebSockt\n")
  tt_handle <- tk_keyboard(thesock$send, wait=F, closeSock=thesock$close)
  wsClient <<- thesock
  pkg.env$all_clients <- list(wsClient) #c(pkg.env$all_clients,wsClient)
  str(pkg.env$all_clients)
  thesock$onMessage(function(binary, message) {
    cat("got WS message",message,"\n")
    thesock$send(message)
    #pkg.env$all_clients <- pkg.env$all_clients[pkg.env$all_clients != wsClient]
    #str(pkg.env$all_clients)
  })
  thesock$onClose(function(){tkdestroy(tt_handle)})
}

app <- list(call=process_request, onWSOpen = processWS)

#' Start the WebServer
#' @export
ws <- function(){

cat('Now do: browseURL("http://localhost:2908/")\n')

httpuv::runServer("0.0.0.0", 2908, app, 250)
#server <- httpuv::startDaemonizedServer("0.0.0.0", 2908, app)
}
#ws()

#' @export
#' @import httpuv
startTheDeamonServer <- function(){
  try(pkg.env$server_handle <- httpuv::startDaemonizedServer("0.0.0.0", 2908, app))
  cat("Started deamon server: ",pkg.env$server_handle,"\n")
  invisible(pkg.env$server_handle)
}

broadcastRefresh <- function(){
  for(ws in pkg.env$all_clients){
    cat("Sending reload_data to ")
    try(ws$send("reload_data"))
  }
}

pkg.env$server_handle <- NULL

.onAttach <- function(libname, pkgname){
  if(interactive()) startTheDeamonServer()
}


.onDetach <- function(libpath){
  cat("Detaching!!!\n")
  stopTheDeamonServer()
}
.onUnload <- function(libpath){
  cat("Unloading!!!\n")
  stopTheDeamonServer()
}


#' @export
.Last.lib <- function(libpath){
  cat("Detaching or Unloading via .Last.lib!!!\n")
  stopTheDeamonServer()
}

#' @export
stopTheDeamonServer <- function(){
    if(is.null(pkg.env$server_handle))
    return()
  cat("Stopping Deamon Server ",pkg.env$server_handle,"... ")
  try(httpuv::stopDaemonizedServer(pkg.env$server_handle))
  pkg.env$server_handle <- NULL
  cat("succeeded\n")
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
    system("route -n get default|grep interface|sed 's/^.*: //' | xargs ifconfig | grep 'inet ' | sed 's/.*inet \\([0-9.]*\\) .*/\\1/'", intern=TRUE)
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
  url <- paste0("http://",host,":",port,"/plotVR.html")
  return(url)
}

#' @export
showQR <- function(...){
  require(qrcode)

  url <- getUrl(...)
  # viewer <- getOption('viewer')
  # viewer()
  qrcode_gen(url)
  invisible(url)
}

#' @export
openViewer <- function(...){
  url <- getUrl(...)
  viewer <- getOption('viewer')
  viewer(url)

  invisible(url)
}

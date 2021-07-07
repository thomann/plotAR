
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

#' Get the URL to which to connect to.
#'
#' @param host the host of the URL - if \code{NULL} will be guessed.
#' @param port the port to connect to
#' @param useIP if \code{TRUE} will guess the IP instead of hostname. Connecting to IPs should be less hassle in most situations where
#' the device and the server are on the same subnet behind a NAT (e.g. at home) or behind a firewall (i.e. in a company).
#' @param useFullName get the hostname from System$getHostname.
#'
#' @return an URL string to connect to
#' @export
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
  # url <- paste0("http://",host,":",port,"/plotAR.html")
  url <- paste0("http://",host,":",port,"/")
  return(url)
}

openViewer <- function(...){
  url <- getUrl(...)
  viewer <- getOption('viewer')
  viewer(url)

  invisible(url)
}


#' Open Keyboard (in the viewer pane if in RStudio).
#' @export
openController <- function(host=getOption("plotAR.external.url")){
  viewer <- getOption("viewer")
  if(is.null(viewer)){
    viewer <- utils::browseURL
    ## So we probably are not in RStudio
    if(is.null(host))
      host <- getUrl()
  }else{
    if(is.null(host))
      host <- getUrl(host='localhost', useIP=FALSE)
  }
  if(is.function(host))
    url <- host('keyboard.html')
  else
    url <- paste0(host, 'keyboard.html')
  viewer(url)
  invisible(url)
}




makeXBM <- function(data){
  n <- ncol(data)
  m <- nrow(data)
  padding <- 8*ceiling(n/8) - n
  raw <- apply(data, 1, function(row)
    packBits(c(as.integer(row),rep(0L,padding)),type='raw')
  )
  raw <- as.raw(raw)
  s <- paste('0x',as.character(raw),sep='',collapse=', ');
  paste(
    "#define test_width ", n, "\n",
    "#define test_height ", m, "\n",
    "static char test_bits[] = {", "\n",
    s, "\n",
    "};", "\n",
    sep=""
  )
}

zoom <- function(data, times){
  apply(data, 2, function(col)
    rep(col,each=times)
  )[,rep(1:nrow(data),each=times)]
}

getQRCode <- function(url){
  qr <- qrcode_gen_patch(url, dataOutput=TRUE, plotQRcode=FALSE)
  return(qr)
}

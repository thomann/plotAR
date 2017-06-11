

defaultSpeed <- 0;


writeData <- function(data,col=NULL,speed=NULL,loc="./data.json",autoScale=T){
  if(is.null(speed)){
    speed <- defaultSpeed
    defaultSpeed <- as.integer(defaultSpeed==0)
  }
  str(data)
  data <- data[,1:3]
  if(!is.null(col)){
    col <- as.integer(col)
    col - min(col)
    data <- cbind(data,col=col)
  }

  ### Removing the NAs
  I <- !apply(is.na(data),1,any)
  data <- data[ I ,]

  ### Auto Scaling
  if(autoScale) data[,1:3] <- as.data.frame(scale(data[,1:3]))
  str(data)

  data_frag <- do.call(paste,c(data,collapse="],[",sep=","))
  #write(paste("var data = [[ ",data_frag,"]];\nvar speed=",speed,"\n"),loc)
  data_json <- paste('{ "data": [[ ',data_frag,']],\n"speed": ',speed,'\n}\n')
  if(!is.null(loc)) write(data_json,loc)
  invisible(data_json)
}
#writeData(threedim)
#writeData(iris[,1:3],col=iris$Species)

#' Plot data into the Cardboard VR
#'
#' This is the main function for usage of plotVR.
#' If necessary it starts a deamonized server and posts the data on that server.
#' If no controller is open one also will be opened.
#' All connected devices will be informed of the new data and should reload the data.
#'
#' @param data data frame of which the first three columns will be used in the scatter.
#' @param col the color for all the points
#' @param broadcast can specify another server to use.
#'
#' @export
#' @seealso \code{\link{open}}
#' @examples
#' \dontrun{
#' plotVR(iris, col=iris$Species)
#' }
plotVR <- function(data, col=NULL, broadcast=getOption('plotVF.default.broadcast', broadcastRefresh)){
  data_json <- writeData(data[,1:3],col=col,loc=NULL)
  broadcast(data_json)
  openController()
  invisible(data_json)
}

#' Broadcast to a server via POST - hence this can run in another process or even on another host.
#'
#' @param data the JSON-model data to broadcast, from \link{writeData}
#' @param server to which post to post the data, default is to \link{getURL} but also can be set
#' using \code{options(plotVR.broadcast.server="http://example.com:2908")}.
#' @param ... passed to \code{\link{httr::POST}}.
#'
#' @return invisible the response of the server
#' @export
#' @seealso \code{\link{openController}}
#'
#' @examples
#'
#' \dontrun{
#' options(plotVF.default.broadcast=broadcastPost)
#' plotVR(iris)
#'
#' # or directly:
#' plotVR(iris, broadcast=broadcastPost)
#' }
broadcastPost <- function(data, server=getOption('plotVR.broadcast.server',plotVR:::getUrl()), ...){
  ret <- httr::POST(server,body=data, ...)
  openController()
  invisible(ret)
}

startExternalServerProcess <- function(){
  R <- '"options(plotVR.log.info=T); plotVR::startBlockingServer()"'
  cmd <- paste0(R.home('bin'),'/Rscript -e ', R)
  system(cmd, wait=FALSE)
}

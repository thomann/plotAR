

defaultSpeed <- 0;

#' Plot data into the Cardboard VR
#'
#' This is the main function for usage of plotVR.
#' If necessary it starts a deamonized server and posts the data on that server.
#' If no controller is open one also will be opened.
#' All connected devices will be informed of the new data and should reload the data.
#'
#' @param data data frame of which the first three columns will be used in the scatter.
#' @param col the color
#' @param size the size
#' @param type point (p) or line (l)
#' @param lines if you want to have lines addition to data
#' @param label text labels of data
#' @param name the name of this dataset - by default will be inferred from \code{data}.
#' @param description description of the data
#' @param speed the speed along which the viewer will fly through data
#' @param autoScale standardize data before sending
#' @param digits precision of data sent
#' @param doOpenController after sending, should the controller be (re-)opened?
#' @param .send send the data
#'
#' @export
#' @seealso \code{\link{open}}
#' @examples
#' \dontrun{
#' plotVR(iris, col=iris$Species)
#' }
plotVR <- function(data,col=NULL, size=NULL, type='p', lines=NULL, label=NULL,
           name=NULL, description=NULL, speed=0L, autoScale=T,
           digits=5, doOpenController=TRUE, .send=TRUE){
  if(is.null(name)) name <- deparse(substitute(data))
  if(is.null(speed)){
    speed <- defaultSpeed
    defaultSpeed <- as.integer(defaultSpeed==0)
  }
  data <- data[,1:3]
  if(!is.null(col)){
    col <- as.integer(col)
    col - min(col)
    data <- cbind(data,col=col)
  }

  ### Removing the NAs
  I <- !apply(is.na(data),1,any)
  data <- data[ I ,]

  n <- nrow(data)

  ### Auto Scaling
  if(autoScale) data[,1:3] <- as.data.frame(scale(data[,1:3]))

  body = list(data=as.matrix(data), speed=speed, protocolVersion='0.3.0')
  if(!is.null(col)) body$col <- col
  if(!is.null(size)) body$size <- size
  if(!is.null(type)) body$type <- type
  if(!is.null(label)) body$label <- label

  if(is.null(name)) name <- deparse(substitute(data))
  metadata <- list(name=name, n=n, created=Sys.time())
  if(is.null(description)) metadata$description <- description
  body$metadata <- metadata

  # TODO auto_unbox is a problem if nrow(data)==1
  if(n==1) warning("There might be a communication problem for nrow(data)==1 - consider adding a second point.")
  data_json <- jsonlite::toJSON(body, auto_unbox=TRUE, digits=digits, pretty=TRUE)

  if(.send) sendData(data_json)
  if(doOpenController) openController()
  invisible(data_json)
}

#' Broadcast to a server via POST - hence this can run in another process or even on another host.
#'
#' @param data the JSON-model data to broadcast, from \link{plotVR}
#' @param server to which post to post the data, default also can be set
#' using \code{options(plotVR.broadcast.server="http://example.com:2908")}.
#' @param ... passed to \code{httr::POST}.
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
sendData <- function(data, server=getOption('plotVR.broadcast.server',plotVR:::getUrl()), ...){
  ret <- httr::POST(server,body=data, ...)
  invisible(ret)
}

#' Start Server
#'
#' @param ... passed to \code{callr::r_bg}
#'
#' @return the process object (invisibly)
#' @export
startServer <- function(...){
  .proc <- callr::r_bg(function(){options(plotVR.log.info=T); plotVR::startBlockingServer()}, ...)
  pkg.env$external.proc <- .proc
  invisible(.proc)
}

#' Stop Server
#'
#' @param ... passed to \code{callr::r_bg}
#'
#' @return the process object (invisibly)
#' @export
stopServer <- function(...){
  pkg.env$external.proc$kill()
}



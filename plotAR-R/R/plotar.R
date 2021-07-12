
#' @export
install_plotar_py <- function(...){
  reticulate::py_install("plotar", pip=TRUE, ...)
}

defaultSpeed <- 0;

#' Plot data into the Cardboard VR
#'
#' This is the main function for usage of plotAR.
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
#' plotAR(iris, col=iris$Species)
#' }
plotAR_ <- function(data, x=NULL, y=NULL, z=NULL, col=NULL, size=NULL, label=NULL,
           name=NULL, description=NULL, axis_names=NULL, col_labels=NULL,
           speed=0L, autoScale=TRUE,
           type='p', lines=NULL, 
           digits=5, doOpenController=TRUE, .send=TRUE){
  
  if(is.null(name)) name <- lazyeval::expr_text(data)
  
  ### Removing the NAs
  I <- !apply(is.na(data),1,any)
  data <- data[ I ,]
  
  n <- nrow(data)
  
  if(is.null(speed)){
    speed <- defaultSpeed
    defaultSpeed <- as.integer(defaultSpeed==0)
  }
  # data <- data[,1:3]
  if(!is.null(col)){
    col <- as.factor(lazyeval::f_eval(col, data))
    if(is.null(col_labels) && is.factor(col)) col_labels <- levels(col)
    # protocol is 0 based:
    col <- as.integer(col) - 1
  }
  
  # if(is.null(axis_names)) axis_names <- rep("",3)
  
  i <- 1
  if(is.null(x)){
    # axis_names[i] <- if(!is.null(colnames(data))) colnames(data)[i]
    x <- data[,i]
  }else{
    # axis_names[i] <- lazyeval::expr_text(x)
    x <- lazyeval::f_eval(x, data)
  }
  
  i <- 2
  if(is.null(y)){
    # axis_names[i] <- if(!is.null(colnames(data))) colnames(data)[i]
    y <- data[,i]
  }else{
    # axis_names[i] <- lazyeval::expr_text(y)
    y <- lazyeval::f_eval(y, data)
  }
  
  i <- 3
  if(is.null(z)){
    # axis_names[i] <- if(!is.null(colnames(data))) colnames(data)[i]
    z <- data[,i]
  }else{
    # axis_names[i] <- lazyeval::expr_text(z)
    z <- lazyeval::f_eval(z, data)
  }
  
  if(!is.null(size)) {
    size <- lazyeval::f_eval(size, data)
    # scale the sizes between 0.5 and 1.5:
    size <- (size-min(size))/diff(range(size)) + 0.5
  }
  
  if(!is.null(label)) {
    label <- as.character(lazyeval::f_eval(label, data))
  }
  
  if(!is.null(lines)) {
    lines <- if(lines == ~TRUE) rep(1, n) else lazyeval::f_eval(lines, data)
    my_col <- if(is.null(col)) rep(0, n) else col
    lines <- lapply(by(data.frame(col=my_col, line=lines, i=seq_len(n)-1), list(my_col, lines), function(x){
      list(col=x$col[1], width=1, points=x$i)
    }, simplify = FALSE), function(x)x)
  }
  
  ### Auto Scaling
  if(autoScale){
    # scale between -1 and 1
    f <- function(x) (x-min(x))/diff(range(x)) * 2 - 1
    x <- f(x)
    y <- f(y)
    z <- f(z)
  }

  body <- list(data=as.matrix(cbind(x,y,z)), speed=speed, protocolVersion='0.3.0')
  if(!is.null(col)) body$col <- col
  if(!is.null(size)) body$size <- size
  if(!is.null(label)) body$label <- label
  if(!is.null(type)) body$type <- type
  if(!is.null(col_labels)) body$col_labels <- col_labels
  if(!is.null(axis_names)) body$axis_names <- axis_names
  if(!is.null(lines)) body$lines <- lines

  if(is.null(name)) name <- deparse(substitute(data))
  metadata <- list(name=name, n=n, created=Sys.time())
  if(is.null(description)) metadata$description <- description
  body$metadata <- metadata
  
  # TODO auto_unbox is a problem if nrow(data)==1
  if(n==1) warning("There might be a communication problem for nrow(data)==1 - consider adding a second point.")
  data_json <- jsonlite::toJSON(body, auto_unbox=TRUE, digits=digits, pretty=TRUE)

  if(.send) sendData(data_json)
  if(doOpenController) openController()
  invisible(body)
}

#' plotAR
#' @export
plotAR <- function(data, x, y, z, col, size, lines, label, type='p',
                   axis_names=NULL,
                    ...){
  if(is.null(axis_names)) {
    if( !is.null(colnames(data)) || !all(c(missing(x),missing(y),missing(z))) ){
      axis_names <- if(is.null(colnames(data))) rep("",3) else colnames(data)[1:3]
      if(!missing(x)) axis_names[1] <- lazyeval::expr_text(x)
      if(!missing(y)) axis_names[2] <- lazyeval::expr_text(y)
      if(!missing(z)) axis_names[3] <- lazyeval::expr_text(z)
    }
  }
  plotAR_(data,
          if(missing(x)) NULL else lazyeval::f_capture(x),
          if(missing(y)) NULL else lazyeval::f_capture(y),
          if(missing(z)) NULL else lazyeval::f_capture(z),
          # lazyeval::f_capture(y), lazyeval::f_capture(z),
          col=if(missing(col)) NULL else lazyeval::f_capture(col),
          size=if(missing(size)) NULL else lazyeval::f_capture(size),
          label=if(missing(label)) NULL else lazyeval::f_capture(label),
          lines=if(missing(lines)) NULL else lazyeval::f_capture(lines),
          # col=lazyeval::f_capture(col), =lazyeval::f_capture(size), label=lazyeval::f_capture(label),
          axis_names=axis_names,
          ...
          )
}


#' @export
surfaceAR <- function(z, doOpenController=TRUE, .send=TRUE, digits=5){
  # first simple implementation for surface using python implementation
  # TODO populate the body just in R
  plotar <- reticulate::import("plotar")
  body <- plotar$surfacevr(z, return_data=TRUE, push_data=FALSE)
  
  data_json <- jsonlite::toJSON(body, auto_unbox=TRUE, digits=digits, pretty=TRUE)
  if(.send) sendData(data_json)
  if(doOpenController) openController()
  invisible(body)
}


#' Broadcast to a server via POST - hence this can run in another process or even on another host.
#'
#' @param data the JSON-model data to broadcast, from \link{plotAR}
#' @param server to which post to post the data, default also can be set
#' using \code{options(plotAR.broadcast.server="http://example.com:2908")}.
#' @param ... passed to \code{httr::POST}.
#'
#' @return invisible the response of the server
#' @export
#' @seealso \code{\link{openController}}
#'
#' @examples
#'
#' \dontrun{
#' options(plotAR.internal.url=broadcastPost)
#' plotAR(iris)
#'
#' # or directly:
#' plotAR(iris, broadcast=broadcastPost)
#' }
sendData <- function(data,
                     server=getOption('plotAR.internal.url',plotAR:::getUrl()),
                     auth=getOption('plotAR.internal.auth',""), ...){
  ret <- httr::POST(server,body=data, httr::add_headers(Authorization=auth), ...)
  invisible(ret)
}

#' Start Server
#'
#' @param ... passed to \code{callr::r_bg}
#'
#' @return the process object (invisibly)
#' @export
startServer <- function(...){
  .proc <- callr::r_bg(function(){
    server <- reticulate::import("plotar.server")
    server$`_start_server`()
  }, ...)
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

#' @export
connectServer <- function(url){
  u <- httr::parse_url(url)
  path <- strsplit(u$path,'/')[[1]]
  if(length(path)>0 && grepl('\\.html$|\\.json$', path[length(path)])){
    path <- path[-length(path)]
  }
  path <- paste(path, collapse="/")
  u2 <- u
  u2$path <- paste0(path, '/')
  u2$query$token <- NULL
  message(httr::build_url(u2))
  "https://hub.gke2.mybinder.org/user/thomann-plotar-6sy8ghsu/plotar/keyboard.html?token=e9mbARgtR1-ieBp0vTnGuw"
  options(plotAR.internal.url=httr::build_url(u2))
  if(!is.null(u$query$token))
    options(plotAR.internal.auth=paste0("token ",u$query$token))
  u$path <- paste0(path, '/keyboard.html')
  message(httr::build_url(u))
  options(plotAR.external.url=function(x=""){
    u$path <- paste0(path, '/', x)
    httr::build_url(u)
  })
}

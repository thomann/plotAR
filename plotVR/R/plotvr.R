

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
#' @export
plotVR <- function(data,col=NULL){
  pkg.env$vr_data_json <- writeData(data[,1:3],col=col,loc=NULL)
  broadcastRefresh()
  invisible(pkg.env$vr_data_json)
}

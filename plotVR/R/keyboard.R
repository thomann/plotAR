startKeyboard <- function(callback){
  callback("hello there")
  while(true){
    msg <- readline()
    callback(msg)
  }
}

parseKey <- function(K,s,k,N){
  modNames <- c('Shift','Ctrl','Alt')
  if(Sys.info()['sysname']=="Linux"){
    ## s on debian: 1-Shift 4-Ctrl 16-NumLock 8-Alt
    thebits <- 2^c(0,2,3)
    ## now on mac ctrl is not mapped...
  }else if(Sys.info()['sysname']=="Darwin"){
    ## s on Mac: 1-Shift 4-Ctrl 16-Cmd 8192-Alt
    thebits <- 2^c(0,4,13)
  }else if(Sys.info()['sysname']=="Windows"){
    ## s on windows: 1-Shift 4-Ctrl 8-NumLock 17-Alt_L 18-Alt_R
    thebits <- c(1,4,2**17 + 2**18)
  }else{
    warning("OS unknown hence no modifiers")
    return(K)
  }

  key <- K
  mods <- as.integer(s)
  if(mods > 0){
    I <- sapply(thebits,function(i)bitwAnd(mods,i)>0)
    if(any(I)){
      mods <- paste(modNames[I],collapse="-")
      key <- paste0(key,"-",mods)
    }
  }
  return(key)
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


tk_keyboard <- function(callback=cat,wait=F,closeSock=NULL, link=NULL){
  library(tcltk)
  tt <- tktoplevel()

  tktitle(tt) <- 'plotVR - controller'

  makeButton <- function(key, name=key, row, col, ...){
    bb <- ttkbutton(tt,text=paste0(name,' (',key,')'),command=function() callback(key))
    tkgrid(bb, row=row, column=col, ...)
  }

  makeButton('r','reload device', 0, 1, columnspan=2)
  makeButton('Space','Toggle flying', 0, 3, columnspan=2)
  makeButton('Esc','quit', 0, 5, columnspan=2)

  makeButton('q','down', 1, 1)
  makeButton('w','forward', 1, 2)
  makeButton('e','up', 1, 3)
  makeButton('a','left', 2, 1)
  makeButton('s','backward', 2, 2)
  makeButton('d','right', 2, 3)

  makeButton('Up','rotate up', 1,5)
  makeButton('Left','rotate left', 2,4)
  makeButton('Down','rotate down', 2,5)
  makeButton('Right','rotate right', 2,6)
  makeButton('d','right', 2, 3)

  if(!is.null(link) && require('qrcode')){
    image1 <- tclVar()
    qr <- qrcode_gen(link, dataOutput=TRUE, plotQRcode=FALSE)
    imageStr <- makeXBM(zoom(qr,4))
    tkimage.create('bitmap',image1, data=imageStr, background='white')
    tkgrid(tklabel(tt, image=image1),row=0,column=0,rowspan=4)
  }

  pkg.env$connectedText <- tclVar("0")
  connectedLabel <- tklabel(tt, textvariable = pkg.env$connectedText)
  tkgrid(tklabel(tt, text='Connected:'), row=3, column=1)
  tkgrid(connectedLabel, row=3, column=2)
  if(!is.null(link))
    tkgrid(tklabel(tt, text=link), row=3, column=3, columnspan=3)


  tkbind(tt, '<Key>', function(K,s,k,N){
    key <- parseKey(K,s,k,N)
    if(K %in% c("Escape","Return")){
      callback("byebye")
      if(!is.null(closeSock)){
        if(is.function(closeSock))
          closeSock()
        else if(closeSock==TRUE)
          tkdestroy(tt)
      }
    }else{
      callback(key)
    }
    #str(list(K=K,s=s,k=k,N=N))
    #str(c(s,mods))
  })

  # FIXME find out how to obtain the close event of the window...
  tcl("wm", "protocol", tt, "WM_DELETE_WINDOW", function(...){
    cat('User is closing window\n')
    str(list(...))
    stopDeamonServer()
  })

  if(wait) tkwait.window(tt)
  tt
}

#tkk <- tk_keyboard(wait=T,closeSock=TRUE,link="http://10.0.0.26:2908")
#tkWait()

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

tk_keyboard <- function(callback=cat,wait=F,closeSock=NULL){
  library(tcltk)
  tt <- tktoplevel()
  tkpack(tkbutton(tt,text='continue',command=function() tkdestroy(tt)), side='bottom')
  tkbind(tt, '<Key>', function(K,s,k,N){
    key <- parseKey(K,s,k,N)
    if(K %in% c("Escape","Return")){
      callback("byebye")
      tkdestroy(tt)
      closeSock()
    }else{
      callback(key)
    }
    #str(list(K=K,s=s,k=k,N=N))
    #str(c(s,mods))
  })
  if(wait) tkwait.window(tt)
  tt
}
#tkWait()

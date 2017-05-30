#!/bin/bash
Rscript -e 'options(plotVR.log.info=T); plotVR::startBlockingServer()'
#(echo 'library(plotVR); options(plotVR.log.info=T); startDeamonServer()'; cat) | R --no-save

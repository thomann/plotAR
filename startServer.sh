#!/bin/bash
(echo 'library(plotVR); options(plotVR.log.info=T); startDeamonServer()'; cat) | R --no-save

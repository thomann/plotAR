library(tidyverse)
library(plotAR)

# do not start server if we are on mybinder.org - there it is already running and configured
if(!getOption("binderhub", FALSE))
  startServer()


iris %>% plotAR(col=Species)









gap <- read.csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminderDataFiveYear.csv') %>%
  filter(continent=='Europe') %>% mutate_if(is.factor, fct_drop) %>% glimpse
gap %>% plotAR(gdpPercap, year, lifeExp, col=country, size=pop, lines=TRUE)







bm <- rnorm(3*1000, sd=1/1000) %>% matrix(ncol=3) %>% apply(2, cumsum)

bm %>% plot(type='l')

bm %>% plotAR(lines=T)




surfaceAR(volcano)


#!/usr/bin/env Rscript
suppressPackageStartupMessages(library(ape))
arg <- grep('^--file=',commandArgs(),value=TRUE)
root <- dirname(normalizePath(sub('^--file=','',arg)))
con <- read.tree(file.path(root,'results/delta/corrected_full/consensus.newick'))
labels <- c('Kalmer 1955','Herzfeldt 1958','Beijing 1976','Kraft 1979','Oberbaum 1980',
  'Enlin-Herrmann 1981','Kubin 1994','Pengkun 2019','Kubin 2024')
names(labels)<-sort(con$tip.label);con$tip.label<-unname(labels[con$tip.label])
pdf(file.path(root,'figures/Fig02_Delta.pdf'),width=9,height=6.6,useDingbats=FALSE)
par(mar=c(1,1,1,1))
plot(con,type='unrooted',lab4ut='horizontal',cex=1.1,font=1,show.tip.label=FALSE,
     no.margin=FALSE,label.offset=.1)
xy<-get('last_plot.phylo',envir=.PlotPhyloEnv)
for(i in seq_along(con$tip.label)) {
  left <- con$tip.label[i] %in% c('Kalmer 1955','Pengkun 2019','Enlin-Herrmann 1981')
  right <- con$tip.label[i] %in% c('Oberbaum 1980','Kubin 2024','Kubin 1994','Herzfeldt 1958')
  x<-xy$xx[i]+ifelse(left,-.1,ifelse(right,.1,0))
  y<-xy$yy[i]+ifelse(con$tip.label[i] %in% c('Beijing 1976','Kraft 1979'),-.2,0)
  text(x,y,con$tip.label[i],adj=ifelse(left,1,ifelse(right,0,.5)),cex=1.05,xpd=NA)
}
dev.off()

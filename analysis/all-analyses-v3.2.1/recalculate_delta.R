#!/usr/bin/env Rscript
# Recompute classic Delta and the five-tree majority consensus, without text resampling.
suppressPackageStartupMessages({library(stylo);library(ape);library(jsonlite)})
arg <- grep('^--file=',commandArgs(),value=TRUE)
root <- dirname(normalizePath(sub('^--file=','',arg)))
out <- file.path(root,'results','delta')
dir.create(out,recursive=TRUE,showWarnings=FALSE)
tasks <- list(c('legacy','full'),c('repairs_only','full'),c('corrected','full'),
              c('corrected','pref'),c('corrected','diary'))
reports <- list()
for (task in tasks) {
  key <- paste(task,collapse='_')
  work <- file.path(out,key); dir.create(work,showWarnings=FALSE)
  corpus <- file.path(root,'results','corpora',task[1],task[2])
  stopifnot(length(list.files(corpus,pattern='txt$'))==9)
  # Set defaults explicitly to retain the original analytical convention.
  fit <- stylo(corpus.dir=corpus,path=work,gui=FALSE,
    corpus.lang='English.all',encoding='UTF-8',preserve.case=FALSE,
    mfw.min=100,mfw.max=500,mfw.incr=100,culling.min=0,culling.max=0,
    distance.measure='delta',linkage='ward.D',analysis.type='BCT',
    sampling='no.sampling',consensus.strength=0.5,
    display.on.screen=FALSE,write.pdf.file=FALSE,write.png.file=FALSE,
    write.jpg.file=FALSE,write.svg.file=FALSE,use.existing.freq.tables=FALSE,
    use.existing.wordlist=FALSE,save.distance.tables=FALSE)
  freq <- fit$table.with.all.freqs
  trees <- list(); levels <- list()
  for (m in seq(100,500,100)) {
    x <- freq[,seq_len(m),drop=FALSE]
    stopifnot(all(apply(x,2,sd)>0))
    delta <- as.matrix(dist.delta(x))
    if (m==500) stopifnot(max(abs(delta-fit$distance.table))<1e-12)
    trees[[as.character(m)]] <- as.phylo(hclust(as.dist(delta),method='ward.D'))
    nearest <- lapply(seq_len(nrow(delta)),function(i) {
      v <- delta[i,]; v[i]<-Inf
      list(witness=rownames(delta)[i],nearest=names(v)[which.min(v)],distance=min(v))
    })
    levels[[as.character(m)]] <- list(features=colnames(x),witnesses=rownames(delta),
       matrix=unname(delta),nearest=nearest)
  }
  class(trees)<-'multiPhylo'
  con <- consensus(trees,p=0.5)
  write.tree(trees,file=file.path(work,'trees_100_500.newick'))
  write.tree(con,file=file.path(work,'consensus.newick'))
  # Record every non-trivial split and its support among the five parameter settings.
  splits <- prop.part(trees)
  split_records <- lapply(seq_along(splits),function(i) list(
    members=attr(splits,'labels')[splits[[i]]],count=attr(splits,'number')[i]))
  reports[[key]] <- list(levels=levels,splits=split_records,
    consensus_newick=write.tree(con),tokenizer='stylo English.all',linkage='ward.D')
  if (key=='corrected_full') {
    labelmap <- c('Kalmer 1955','Herzfeldt 1958','Beijing 1976','Kraft 1979','Oberbaum 1980',
      'Enlin-Herrmann 1981','Kubin 1994','Pengkun 2019','Kubin 2024')
    names(labelmap) <- sort(con$tip.label)
    con$tip.label <- unname(labelmap[con$tip.label])
    figdir <- file.path(root,'figures');dir.create(figdir,showWarnings=FALSE)
    pdf(file.path(figdir,'Fig02_Delta.pdf'),width=10,height=7.2,useDingbats=FALSE)
    par(mar=c(1,1,1,1));plot(con,type='unrooted',lab4ut='horizontal',cex=1.1,
      font=1,no.margin=FALSE,label.offset=.1)
    dev.off()
  }
}
write_json(list(R=as.character(getRversion()),stylo=as.character(packageVersion('stylo')),
  ape=as.character(packageVersion('ape')),analyses=reports),file.path(out,'delta_results.json'),
  pretty=TRUE,auto_unbox=TRUE,digits=16)

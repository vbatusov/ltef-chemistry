#!/usr/bin/bash
# lowerit
# convert all file names in the current directory to lower case
# only operates on plain files--does not change the name of directories
# will ask for verification before overwriting an existing file
for x in ./* 
  do
  echo "Looking at $x..."
  lc=`echo $x | tr '[A-Z]_ ' '[a-z]_'`
  mv -i "$x" $lc
done

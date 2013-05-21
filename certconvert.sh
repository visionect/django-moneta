#!/bin/bash 

if [ $# -eq 0 ]
  then
    echo "Usage: ./certconvert.sh db_location mobitel_root_ca client_p12"
  else
  	mkdir -p $1
  	certutil -N -d $1
  	certutil -d $1 -A -n "MobitelCA" -t "CTu,C,C" -i $2
  	pk12util -d $1 -i $3
  	echo "Done!"
fi


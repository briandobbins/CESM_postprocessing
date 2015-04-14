#!/bin/sh
#
# script to setup the python virtual environment for postprocessing
#
#-----------------
# Created on April 2, 2015
#
# Author: CSEG <cseg@cgd.ucar.edu>
#

#======================================================================
# Local functions
#======================================================================

function Usage {
    echo "SYNOPSIS"
    echo "     $progname [options]"
    echo ""
    echo "     This script sets up the python virtual environment (env) for a given supported machine."
    echo "     This script executes the following steps:"
    echo "     - loads the python modules for this machine necessary to boot-strap the env"
    echo "     - make env"
    echo "     - activate env"
    echo "     - install post-processing tools into the env"
    echo "     - compile/install additional tools (e.g. zonal_average tool for ocn diag)"
    echo "     - run unittests"
    echo "     - deactivate env"
    echo ""
    echo "OPTIONS"
    echo "     -machine_dir           specify a CESM supported machine directory where the"
    echo "                            [machine]_modules.sh script resides"
    echo "     -machine               specify a CESM supported machine name"
    echo "     -help                  Print this help message and exit"
}

#======================================================================
# Given a relative path, convert to an absolute path
# (from http://www.lancejian.com/2011/04/13/get-absolute-path-of-the-running-bash-script.html)
function absolute_path {
    relative_path="$1"
    absolute_path=`cd "$relative_path"; pwd`
    echo "$absolute_path"
}


# Prints the test status and an info string, separated by ':'
# Inputs:
#   status: test status
#   info: optional auxiliary info about test failure
function print_result {
    status="$1"
    info="$2"
    
    echo "${status}:${info}"
}

#======================================================================
# Begin main script
#======================================================================

progname=`basename $0`

# need absolute path (rather than relative path) because we use this
# path to get to the machines directory
pp_dir=$(absolute_path `dirname $0`)  

#----------------------------------------------------------------------
# Set default return values
#----------------------------------------------------------------------
status='UNDEF'
info=''

#----------------------------------------------------------------------
# Define default values for command-line arguments
#---------------------------------------------------------------------- 
machine_dir="${pp_dir}/machines"
echo $machine_dir
machine=''

#----------------------------------------------------------------------
# Process command-line arguments
#----------------------------------------------------------------------
while [ $# -gt 0 ]; do
    case $1 in
        -machine_dir )
            machine_dir=$2
            shift
            ;;
        -machine )
            machine=$2
            shift
            ;;
        -help )
            Usage
            exit 0
            ;;
        * )
            echo "$progname: Unknown argument: $1" >&2
            echo "Run $progname -help for usage" >&2
	    print_result $status "$info"
            exit 1
            ;;
    esac
    shift
done


#----------------------------------------------------------------------
# Exit if required command-line arguments weren't provided
#----------------------------------------------------------------------
error=0  # no errors yet

if [ -z $machine_dir ]; then
    status="WARNING"
    info="$progname: machine_dir not specified. Using ${pp_dir}/machines." >&2
    error=0
fi
if [ -z $machine ]; then
    status="ERROR"
    info="$progname: A valid, supported machine name must be provided." >&2
    error=1
fi

if [ $error -gt 0 ]; then
    echo "" >&2
    echo "Run $progname -help for usage" >&2
    # return default values for status & info
    print_result $status "$info"
    exit 1
fi

#----------------------------------------------------------------------
# Determine whether [machine_dir]/[machine]_modules.sh file exists
#----------------------------------------------------------------------
module_script="${machine_dir}/${machine}_modules.sh"
if [ ! -x $module_script ]; then
    status="ERROR"
    info="$progname - ${module_script} does not exist. Please check input options."
    print_result $status "$info"
    exit 0
fi

#----------------------------------------------------------------------
# load the python boot-strap modules for this machine
#----------------------------------------------------------------------
. $module_script

#----------------------------------------------------------------------
# check if cesm-env2 already exists, if so exit
#----------------------------------------------------------------------
env="${pp_dir}/cesm-env2"
echo $env
if [ -f $env ]; then
    status="ERROR"
    info="$progname - ${pp_dir}/cesm-env2 virtual environment already exists.
It is only necessary to create the virtual environment once in the CESM source tree.
All post processing scripts residing in a CASE directory will activate and deactivate
the virtual environment as necessary. 

If a new or updated virtual environment needs to be created then following these steps:
>cd ${pp_dir}
>make clobber
>make clobber-env

and rerun this script."
    print_result $status "$info"
    exit 0
fi

curdir=`pwd`
echo $curdir
cd $pp_dir

#----------------------------------------------------------------------
# create the virtual environment. Makefile checks to see if it is
# already setup, so only done once per case.
#----------------------------------------------------------------------
echo "$progname - making virtual environment in ${pp_dir}/cesm-env2."
make env

#----------------------------------------------------------------------
# activate it for this script
#----------------------------------------------------------------------
echo "$progname - activating virtual environment in ${pp_dir}/cesm-env2."
. cesm-env2/bin/activate

#----------------------------------------------------------------------
# install post processing packages
#----------------------------------------------------------------------
echo "$progname - installing all post processing tools into the virtual environment in ${pp_dir}/cesm-env2."
make all

#----------------------------------------------------------------------
# run some self tests
#----------------------------------------------------------------------
echo "$progname - Testing post processing installation by listing the installed modules."
# run unit tests here?

#----------------------------------------------------------------------
# is one of our installed executables in the path?
#----------------------------------------------------------------------
module_check.py

#----------------------------------------------------------------------
# cleanup and deactivate the virtualenv. 
#----------------------------------------------------------------------
deactivate

cd $curdir

status="SUCCESS"
info="$progname - CESM post processing virtual environment installed successfully in 
${pp_dir}/cesm-env2.
All interaction with the virtual environment including activating and deactivating is done via
the post processing tools that reside in the experiment CASE directory and are created 
using the create_postprocessing script. These include:
[CASENAME].timeseries
[CASENAME].diagnostics"
print_result $status "$info"

exit 0
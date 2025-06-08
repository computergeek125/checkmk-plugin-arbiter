#!/bin/bash

NAME=$(python -c 'print(eval(open("package").read())["name"])')
rm /omd/sites/cmk/var/check_mk/packages/* ||:
ln -s $WORKSPACE/package /omd/sites/cmk/var/check_mk/packages/$NAME
echo $WORKSPACE :: $NAME
ls $WORKSPACE /omd/sites/cmk/var/check_mk/packages/
mkp list

mkp -v package package

# Set Outputs for GitHub Workflow steps
if [ -n "$GITHUB_WORKSPACE" ]; then
    echo "pkgfile=$(ls /omd/sites/cmk/local/share/check_mk/enabled_packages/*.mkp)" >> $GITHUB_OUTPUT
    echo "pkgname=${NAME}" >> $GITHUB_OUTPUT
    VERSION=$(python -c 'print(eval(open("package").read())["version"])')
    echo "pkgversion=$VERSION" >> $GITHUB_OUTPUT
firm 

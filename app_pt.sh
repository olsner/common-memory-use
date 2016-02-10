#!/bin/bash

pkg="$1"

if [ $# -ne 1 ]; then
	echo >&2 "Usage: $0 PACKAGE_NAME"
	exit 1
fi

run() {
	echo "\$ $@" >&2
    adb shell run-as $pkg "$@"
}

tempdir=/sdcard
uid="$(run id | sed 's/^uid=[0-9]\+(\([^)]*\)).*$/\1/g')"
adb push pt.py "$tempdir"
pids="$(run ps | grep "^$uid" | awk ' $9 !~ /ps/ { print $2; } ')"
if [ -z "$pids" ]; then
    echo "No matching processes found..."
    exit 1
fi
run ps | grep "^$uid" | awk ' $9 !~ /ps/ { print; } '
run ${dev_python-python} "$tempdir"/pt.py $pids

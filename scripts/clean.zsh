#!/usr/bin/env zsh

setopt ERR_EXIT
setopt NO_UNSET

function usage()
{
    cat <<-'EOF'
		Usage:

		    $ clean.zsh [-d]

		-d  perform deep clean
	EOF
    exit 1
}

deep_clean=false

while getopts :d opt; do
    case $opt in
        d) deep_clean=true ;;
        \?|*) usage ;;
    esac
done

cd -- ${0:h}/..

rm --force --recursive \
    .coverage          \
    build              \
    dist               \
    pyddp.egg-info     \
    docs/build


function rm_pyc()
{
    find $1 -name '*.pyc' -delete
}

rm_pyc ddp
rm_pyc tests

if $deep_clean; then
    rm --force --recursive local/venv
fi


#!/bin/sh
set -e


usage() {
    echo "Usage: $0 <src_fn> [inp_fn]"
    exit 1
}


src_fn=$1
[ -z "$src_fn" ] && usage

inp_fn=$2
[ -z "$inp_fn" ] && usage

if [ "$inp_fn" = "--" ]; then
    # no filename provided, read stdin
    inp_fn=$(mktemp)
    cat > $inp_fn
elif [ ! -f "$inp_fn" ]; then
    echo "Invalid source file \"$inp_fn\""
    exit 1
fi


asm_fn=$(mktemp)
obj_fn=$(mktemp)
out_fn=$(mktemp)

# Pipenv is so unbearably slow, run python itself
# pipenv run python translator.py -f $src_fn > $asm_fn
python3 translator.py -f $src_fn > $asm_fn
# cat $asm_fn
# exit 0

pep9term asm -s $asm_fn -o $obj_fn
pep9term run -s $obj_fn -i $inp_fn -o $out_fn

cat $asm_fn
cat $out_fn

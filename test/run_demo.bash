#!/usr/bin/env bash
# Runs a little demo of findfunc, for recording with asciinema.
hash findfunc &>/dev/null || {
    printf "FindFunc is not installed!\n" 1>&2
    exit 1
}
verstr="$(findfunc --version)"
printf "\nShowing %s examples.\n" "$verstr"

scripts="${1:-$HOME/scripts}"
declare -A commands=(
    ["Python function"]="findfunc print_err $scripts -m 2"
    ["Python function, containing a string"]="findfunc print_err $scripts -m 2 -c C\\("
    ["Python class"]="findfunc InvalidArg $scripts -m 1"
    ["C function"]="findfunc validate_.+ $scripts/c"
    ["C function signature"]="findfunc validate_.+ $scripts/c -S"
    ["JavaScript function"]="findfunc JSON.+ $scripts/js"
    ["Bash function"]="findfunc ziplist $HOME/bash.alias.sh"
    ["Makefile target"]="findfunc all $scripts/c/cpat/makefile"
)

for cmddesc in "${!commands[@]}"; do
    printf "\nFinding a %s.\n" "$cmddesc"
    cmd="${commands[$cmddesc]}"
    printf "%s\n" "$cmd"
    $cmd || exit 1
    sleep 1
done

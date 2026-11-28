# Sourced by src/main/cli/completions/_corpus-yoga each time tab is pressed: offers what
# the declarations say at that moment. No command or flag is written here.
#
# The declarations read are those of the copy of corpus-yoga being typed - ./corpus-yoga
# in a second copy offers that copy's commands - and of the copy holding this file
# where the word typed names no copy.
local typed=${(Q)words[1]}
# the word typed names the copy: a path, a command on PATH, or the alias the installed block
# writes, which names this copy's launcher - its directory the root, handed to what it starts
[[ $typed == */* ]] || typed=${commands[$typed]:-${aliases[$typed]-}}
typed=${typed/#\~/$HOME}
local copy=${typed:A:h}
local -a ask=(env CORPUS_YOGA_ROOT=$copy "$copy/src/run_python_script.sh" "$copy/src/main/cli/completions/offer.py")
local offered
if offered="$("${ask[@]}" 2>/dev/null)"; then
  eval "$offered"
else
  # said beneath the prompt: a tab that offers nothing and says nothing reads as a
  # position that takes no argument
  _message -r "corpus-yoga offers nothing here - ${${(f)"$("${ask[@]}" 2>&1 >/dev/null)"}[-1]}"
fi

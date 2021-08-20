#compdef run

__runfile_completion () {
    case "${COMP_WORDS[COMP_CWORD]}" in
        -*) suggestions="-l -u -h -f"
            suggestions="$suggestions --bash-completion"
            suggestions="$suggestions --containers"
            suggestions="$suggestions --list-targets"
            suggestions="$suggestions --update"
            suggestions="$suggestions --file"
            suggestions="$suggestions --no-cache"
            ;;
        *)
            filename='Runfile.md'
            file_flag=false
            for word in "${COMP_WORDS[@]}"
            do
                if [ "$file_flag" = true ]
                then
                    filename="$word"
                    file_flag=false
                fi
                if [ "$word" = "-f" ] || [ "$word" = "--file" ]
                then
                    file_flag=true
                fi
            done
            if [ "$file_flag" = true ] || [ "$filename" = "${COMP_WORDS[COMP_CWORD]}" ]
            then
                suggestions=$(compgen -G '*.md')
            else
                suggestions=$(eval "run -f \"$filename\" --list" 2>/dev/null)
            fi
            ;;
    esac
    [ -z "$suggestions" ] && return 0
    COMPREPLY=()
    while read -r suggestion
    do
        COMPREPLY+=("$suggestion")
    done < <(compgen -W "$suggestions" -- "${COMP_WORDS[COMP_CWORD]}")
}

if [[ -n ${ZSH_VERSION-} ]]
then
    if ! command -v compinit > /dev/null
    then
        autoload -U +X compinit && compinit
    fi
    autoload -U +X bashcompinit && bashcompinit
fi

complete -F __runfile_completion run

function mk_cmk_link {
    if [ -e "$1" ];then
        echo "Linking '$1' to '$2'"
        rmdir "$2"
        ln -s "$1" "$2"
    else
        echo "Source directory '$1' does not exist"
    fi
}

if [ -n "$GITHUB_WORKSPACE" ]; then
    mk_cmk_link "$GITHUB_WORKSPACE/plugins" "/opt/omd/sites/cmk/local/lib/python3/cmk_addons/plugins"
else
    echo "Not running in a Github workspace"
fi
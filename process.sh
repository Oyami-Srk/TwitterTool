#!/usr/bin/env zsh

cookie_file="cookie.json"
workdir="working_dir"

# preprocess todo.txt
function preprocess() {
    if [ ! -f "$1" ]; then
        echo Todo file \"$1\" does not exist.
        exit 1
    fi
    local o_tmp_file=`mktemp`
    awk 'match($0, /https:\/\/.*twitter.*\/.*\/status\/[0-9]+/){ print substr($0, RSTART, RLENGTH)}' $1 > $o_tmp_file
    local o_url_count=`wc -l < $o_tmp_file | tr -d ' '`

    if [ $o_url_count = 0 ]; then
        echo Todo file contains no tweets url.
        rm $o_tmp_file
        exit 2
    fi
    if [ `sed '/^[[:space:]]*$/d' $1 | wc -l` != `cat $o_tmp_file | wc -l` ]; then
        echo "File has inregular tweet url(s), Please check by yourself."
    fi

    tmp_file=`mktemp`
    awk '!visited[$0]++' $o_tmp_file > $tmp_file
    rm $o_tmp_file
    url_count=`wc -l < $tmp_file | tr -d ' '`
    echo Raw todo.txt has $o_url_count entries. It has $url_count unduplicated entries.
}

# download twitter webpage
function get() {
    if [ ! -f "$1" ]; then
        echo Links file \"$1\" does not exist.
        exit 3
    fi
    today=`date "+%Y%m%d"`
    logn="log/tweet-$today"
    if [ -f $logn.log ]; then
        local index=1
        while :
        do
            if [ ! -f $logn-$index.log ]; then
                $logn="$logn-$index"
                break
            fi
            (( index++ ))
        done
    fi
    logf=$logn.log

    json_dir="$workdir/json-$today"
    if [ -d $json_dir ]; then
        local index=1
        while :
        do
            if [ ! -d $json_dir-$index ]; then
                json_dir="$json_dir-$index"
                break
            fi
            (( index++ ))
        done
    fi
    echo Output json dir is $json_dir
    mkdir $json_dir

    python3 ./get_tweets.py -i $1 -o $json_dir -C $cookie_file --log $logf --headless
    ret=$?

    failed=`cat $logf | grep Failed | awk '{ print $2 }'`
    failed_num=`echo $failed | wc -l | tr -d ' '`
    restrict=`cat $logf | grep Restrict | awk '{ print $2 }'`
    restrict_num=`echo $restrict | wc -l | tr -d ' '`
    notexists=`cat $logf | grep NotExists | awk '{ print $2 }'`
    notexists_num=`echo $notexists | wc -l | tr -d ' '`

    if [ $failed_num = 0 ]; then
        echo "Awesome, No failed entries for first turn!"
        echo Restirct entries: $restrict_num
        echo NotExists entries: $notexists_num
        return 0
    else
        echo -n "Waiting for retry...5"; sleep 0.5; echo -n .; sleep 0.5; echo -n 4; sleep 0.5; echo -n .; sleep 0.5; echo -n 3; sleep 0.5; echo -n .; sleep 0.5; echo -n 2; sleep 0.5; echo -n .; sleep 0.5; echo -n 1; sleep 0.5; echo -n .; sleep 0.5; echo "0\!"
        local retries=1
        local cfailed=$failed
        while [ $retries -le 3 ]
        do
            echo "Retrying failed entries for $retries times."
            local tmpi=`mktemp`
            echo $cfailed > $tmpi
            local ret_logf=$logn-retry$retries.log
            python3 ./get_tweets.py -i $tmpi -o $json_dir -C $cookie_file --log $ret_logf --headless
            rm $tmpi
            cfailed=`cat $ret_logf | grep Failed | awk '{ print $2 }'`
            local cfn=`echo $cfailed | wc -l | tr -d ' '`
            if [ $cfn = 0 ]; then
                echo Failed entries cleaned.
                break
            fi
            (( retries++ ))
        done
    fi
}

function cock() {
    if [ ! -d $1 ]; then
        echo Json dir \"$1\" does not exists.
        exit 4
    fi
    today=`date "+%Y%m%d"`
    local jn=$workdir/download-$today
    if [ -f $jn.json ]; then
        local index=1
        while :
        do
            if [ ! -f $jn-$index.json ]; then
                $jn="$jn-$index"
                break
            fi
            (( index++ ))
        done
    fi
    local jnf=$jn.json
    python3 ./cock_list.py -o $jnf $1
}

function pack() {
    tar -jcf $1.tar.bz2 $1
}

function all() {
    preprocess $1
    get $tmp_file
    cock $json_dir
    pack $json_dir
}

"$@"


#! /bin/bash

HEADER_CONTENT_TYPE="Content-Type: application/json"
HEADER_ACCEPT="Accept: application/json"
API_KEY="X-Cisco-Meraki-API-Key: bce348a3002d7d58b2c723fb0cb00bd99f02ca88"
BASE_URL="https://dashboard.meraki.com/api/v0"
COMM_FILE="/tmp/rest.json"
CURL_FILE="/tmp/curl.out"

function callGETService {
    local uri=$1
    local certAtt=""

    if [[ -n "$CA_CERT_PATH" ]]; then
        certAtt="--cacert $CA_CERT_PATH"
    fi

    echo "Calling URI (GET):" ${uri}
    curl -L -X GET -H "${API_KEY}" -H "${HEADER_ACCEPT}" -H "${HEADER_CONTENT_TYPE}" "${BASE_URL}${uri}" --output "${COMM_FILE}" 2> /dev/null > "${COMM_FILE}"
}

function callPOSTService {
    local uri=$1
    local json=$2
    local certAtt=""

    if [[ -n "$CA_CERT_PATH" ]]; then
        certAtt="--cacert $CA_CERT_PATH"
    fi

    echo "Calling URI (POST):" ${uri}
    echo "Sending Data:" ${json}
    curl --write-out '{"httpstatus":"%{http_code}"}' -L -X POST -H "${API_KEY}" -H "${HEADER_ACCEPT}" -H "${HEADER_CONTENT_TYPE}" "${BASE_URL}${uri}" --data-binary "${json}" 2> /dev/null > "${COMM_FILE}"
}

function callPUTService {
    local uri=$1
    local json=$2
    local certAtt=""

    if [[ -n "$CA_CERT_PATH" ]]; then
        certAtt="--cacert $CA_CERT_PATH"
    fi

    echo "Calling URI (PUT):" ${uri}
    curl -L -X PUT -H "${API_KEY}" -H "${HEADER_ACCEPT}" -H "${HEADER_CONTENT_TYPE}" "${BASE_URL}${uri}" --data-binary "${json}" 2> /dev/null > "${COMM_FILE}"
}

# get all organizations
function getOrgs {
    callGETService "/organizations"
	# jq doesn't work because it doesn't process large numbers correctly
#     local c=`jq length $COMM_FILE`
#     for ((i=0;i<=c-1;i++)); do
# 	    local d=`jq '.['"$i"'] | .id,.name' $COMM_FILE`
# 	    echo "*" ${d}
# 	done

	local c=`cat $COMM_FILE`
	IFS='%'
	arr=$(echo $c | sed 's/},{/}%{/g' | tr -d "[]")

	for x in $arr
	do
		# add quotes to orgid json
		orgjson=$( echo $x | sed 's/:\([0-9]*\)\([,}]\)/:"\1"\2/g' )
		# parse json to get id and name
		orgid=$( echo $orgjson | grep -o '"id": *"[^"]*"' | grep -o '"[^"]*"$' )
		orgname=$( echo $orgjson | grep -o '"name": *"[^"]*"' | grep -o '"[^"]*"$' )
		echo "*" $orgid $orgname
	done
}

# get all networks
function getNets {
    callGETService "/organizations/$1/networks"
    local c=`jq length $COMM_FILE`
    for ((i=0;i<=c-1;i++)); do
	    local d=`jq '.['"$i"'] | .id,.name' $COMM_FILE`
	    local d=${d/\"/}
	    local d=${d/\"/}
	    echo "*" ${d}
	done
}

# get all devices
function getDevs {
    callGETService "/networks/$1/devices"
    local c=`jq length $COMM_FILE`
    for ((i=0;i<=c-1;i++)); do
	    local d=`jq '.['"$i"'] | .serial,.model,.name // .mac' $COMM_FILE`
	    local d=${d/\"/}
	    local d=${d/\"/}
	    echo "*" ${d}
	done
}

# add network
function newNet {
	local name=$2
	local json='{"name": "'${name}'", "timeZone": "Etc/GMT", "type": "switch appliance wireless"}'
    callPOSTService "/organizations/$1/networks" "${json}"
    local dtmp=`jq '.id' $COMM_FILE`
    local d=`echo $dtmp | cut -d' ' -f1 | sed 's/"//g'`
    if [ -z "$d" ]; then
    	cat $COMM_FILE
    	echo ""
    elif [ $d = "null" ]; then
    	cat $COMM_FILE
    	echo ""
    else
		echo "New network" $d "created."
	fi
}

# add device
function newDev {
	local sn=$2
	local json='{"serial": "'${sn}'"}'
    callPOSTService "/networks/$1/devices/claim" "${json}"
    # local d=`jq '.id' $COMM_FILE`
    local stmp=`jq '.httpstatus' $COMM_FILE`
    local s=`echo $stmp | cut -d' ' -f2 | sed 's/"//g'`
    if [ $s != "200" ]; then
    	cat $COMM_FILE
    	echo ""
    else
		echo "New device" $sn "claimed."
	fi
}

# configure SSID
function setSsid {
	local name=$2
	local psk=$3
	local json='{"name": "'${name}'", "enabled": true, "authMode": "psk", "encryptionMode": "wpa", "wpaEncryptionMode": "WPA2 only", "psk": "'${psk}'"}'
    callPUTService "/networks/$1/ssids/0" "${json}"
    local dtmp=`jq '.number' $COMM_FILE`
    local d=`echo $dtmp | cut -d' ' -f1 | sed 's/"//g'`
    if [ -z "$d" ]; then
    	cat $COMM_FILE
    	echo ""
    elif [ $d = "null" ]; then
    	cat $COMM_FILE
    	echo ""
    else
		echo "SSID" "'"$2"'" "configured."
	fi
}

if [ $# -eq 0 ]
  then
    echo "No arguments supplied"
  else
    POSITIONAL=()
    while [[ $# -gt 0 ]]
    do
      key="$1"

      case $key in
          -O|--organization)
          ORGANIZATION="$2"
          shift # past argument
          shift # past value
          ;;
          -N|--network)
          NETWORK="$2"
          shift # past argument
          shift # past value
          ;;
          -D|--device)
          DEVICE="$2"
          shift # past argument
          shift # past value
          ;;
          -P|--psk)
          PSK="$2"
          shift # past argument
          shift # past value
          ;;
          --default)
          DEFAULT=YES
          shift # past argument
          ;;
          *)    # unknown option
          POSITIONAL+=("$1") # save it in an array for later
          shift # past argument
          ;;
      esac
    done
    set -- "${POSITIONAL[@]}" # restore positional parameters

    echo ORGANIZATION    = "${ORGANIZATION}"
    echo NETWORK         = "${NETWORK}"
    echo DEVICE          = "${DEVICE}"
    echo PSK             = "${PSK}"
	echo ""
  
    case $1 in
    	getorgs)
		    getOrgs
		    ;;
    	getnets)
		    getNets "${ORGANIZATION}"
		    ;;
    	getdevs)
		    getDevs "${NETWORK}"
		    ;;
    	newnet)
		    newNet "${ORGANIZATION}" "$2"
		    ;;
    	newdev)
		    newDev "${NETWORK}" "$2"
		    ;;
    	setssid)
		    setSsid "${NETWORK}" "$2" "${PSK}"
		    ;;
		*)
		    echo "Invalid arguments"
		    ;;
	esac
fi
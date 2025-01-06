#!/bin/bash

#strict mode
set -euo pipefail

LOCKDIR=/tmp/backup.lock

main() {
    if [ -z "$RESTIC_PASSWORD_FILE" ]; then
        echo "RESTIC_PASSWORD_FILE is not set"
        exit 1
    fi

    if [ -z "$RESTIC_REPOSITORY" ]; then
        echo "RESTIC_REPOSITORY is not set"
        exit 1
    fi

    if [ -z "$BACKUP_SOURCE" ]; then
        echo "BACKUP_SOURCE is not set"
        exit 1
    fi

    if ! [ -d "$RESTIC_REPOSITORY" ]; then
        echo "Backup disk $RESTIC_REPOSITORY not found"
        exit 1
    fi

    if ! [ -d "$BACKUP_SOURCE" ]; then
        echo "Backup source $BACKUP_SOURCE not found"
        exit 1
    fi

    echo "finding last snapshot id"
    LAST_SNAPSHOT_ID=$(restic --cache-dir "/tmp/restic-cache" snapshots --tag media --latest 1 --json | jq -r '. | sort_by(.time) | last | .id')
    echo "last snapshot id: $LAST_SNAPSHOT_ID"

    echo "running backup"
    restic backup --cache-dir "/tmp/restic-cache" --exclude '#recycle' --tag media --parent "$LAST_SNAPSHOT_ID" $BACKUP_SOURCE 
}

#Remove the lock directory
cleanup() {
    if rmdir -- "$LOCKDIR"; then
        echo "Finished"
    else
        echo >&2 "Failed to remove lock directory '$LOCKDIR'"
        exit 1
    fi
}

if mkdir -- "$LOCKDIR"; then
    trap "cleanup" EXIT

    echo "Acquired lock, running"
    main
else
    echo >&2 "Could not create lock directory '$LOCKDIR'"
    exit 1
fi
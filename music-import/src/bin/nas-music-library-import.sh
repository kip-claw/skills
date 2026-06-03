#!/bin/bash
# nas-music-import.sh — Helper for importing new music to the beets library on NAS
# Subcommands: status, prepare, check, cleanup, rescan, count

set -e

NAS_MUSIC="/srv/dev-disk-by-uuid-a170c673-36d0-4a82-a615-e7356ef68cc6/Music"
NAS_STAGING="/srv/dev-disk-by-uuid-a170c673-36d0-4a82-a615-e7356ef68cc6/bandcamp-import"
SSH_OPTS="-o ConnectTimeout=5 -o StrictHostKeyChecking=no"

case "$1" in
  status)
    ssh $SSH_OPTS kip-nas "
      if [ ! -d '$NAS_STAGING' ]; then
        echo 'Staging dir does not exist (nothing to process).'
        exit 0
      fi
      cd '$NAS_STAGING'
      zips=\$(find . -maxdepth 1 -type f -name '*.zip' 2>/dev/null | wc -l)
      dirs=\$(find . -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l)
      audio=\$(find . -type f \\( -iname '*.mp3' -o -iname '*.flac' -o -iname '*.m4a' -o -iname '*.wav' \\) 2>/dev/null | wc -l)
      echo \"Zip files at top level: \$zips\"
      echo \"Subdirectories: \$dirs\"
      echo \"Audio files (total, all depths): \$audio\"
      echo
      if [ \$zips -gt 0 ] || [ \$dirs -gt 0 ]; then
        echo '=== Contents ==='
        ls -1
      else
        echo 'Staging is empty.'
      fi
    "
    ;;

  prepare)
    ssh $SSH_OPTS kip-nas "
      if [ ! -d '$NAS_STAGING' ]; then
        echo 'Staging dir does not exist. Have you rsynced files into it yet?'
        echo \"Expected: $NAS_STAGING\"
        exit 1
      fi
      cd '$NAS_STAGING'

      shopt -s nullglob
      extracted=0
      for zip in *.zip; do
        dir=\"\${zip%.zip}\"
        if [ -d \"\$dir\" ]; then
          echo \"Skip (folder already exists): \$dir\"
        else
          echo \"Extracting: \$dir\"
          mkdir -p \"\$dir\"
          unzip -q -o -d \"\$dir\" \"\$zip\"
          rm \"\$zip\"
          extracted=\$((extracted+1))
        fi
      done

      echo
      echo \"Extracted \$extracted zips.\"
      echo
      echo '=== Albums ready to import ==='
      ls -1 2>/dev/null || echo '(staging is empty)'
    "
    ;;

  check)
    ssh $SSH_OPTS kip-nas "
      if [ ! -d '$NAS_STAGING' ]; then
        echo 'Staging dir does not exist.'
        exit 0
      fi
      cd '$NAS_STAGING'
      echo '=== Duplicate check vs existing beets library ==='
      found=0
      shopt -s nullglob
      for dir in */; do
        dir=\"\${dir%/}\"
        # try album name = everything after first ' - '
        album=\$(echo \"\$dir\" | sed -E 's/^[^-]+ - //')
        matches=\$(beet ls -a -f '\$albumartist :: \$album :: \$year' \"album:\$album\" 2>/dev/null)
        if [ -n \"\$matches\" ]; then
          echo \"POTENTIAL DUP: \$dir\"
          echo \"\$matches\" | sed 's/^/  matches: /'
          found=1
        fi
      done
      if [ \$found -eq 0 ]; then
        echo 'No likely duplicates against existing library.'
        echo
        echo 'Ready to import. From a NAS shell, run:'
        echo \"  beet import --noincremental '$NAS_STAGING/'\"
      else
        echo
        echo 'WARNING: at least one staged album appears to already be in the library.'
        echo 'Importing as-is risks the Bartz-pattern crash. Delete one copy from'
        echo 'staging or the library before running beet import.'
      fi
    "
    ;;

  cleanup)
    ssh $SSH_OPTS kip-nas "
      if [ ! -d '$NAS_STAGING' ]; then
        echo 'Staging dir already gone. Nothing to clean up.'
        exit 0
      fi
      audio_remaining=\$(find '$NAS_STAGING' -type f \\( -iname '*.mp3' -o -iname '*.flac' -o -iname '*.m4a' -o -iname '*.wav' -o -iname '*.ogg' -o -iname '*.aac' \\) 2>/dev/null | wc -l)
      if [ \$audio_remaining -eq 0 ]; then
        non_audio=\$(find '$NAS_STAGING' -type f 2>/dev/null | wc -l)
        echo \"No audio files in staging (had \$non_audio non-audio leftovers like cover art / booklets). Removing.\"
        rm -rf '$NAS_STAGING'
        echo 'Cleanup complete.'
      else
        echo \"Staging still has \$audio_remaining audio files. These are likely skipped imports.\"
        echo 'Not removing. Run: nas-music-import.sh status'
        exit 1
      fi
    "
    ;;

  rescan)
    echo '=== Kodi audio library clean ==='
    curl -s -u kodi:kodi \
      -H "Content-Type: application/json" \
      -d '{"jsonrpc":"2.0","method":"AudioLibrary.Clean","id":1}' \
      http://localhost:8080/jsonrpc
    echo
    sleep 2
    echo '=== Kodi audio library scan ==='
    curl -s -u kodi:kodi \
      -H "Content-Type: application/json" \
      -d '{"jsonrpc":"2.0","method":"AudioLibrary.Scan","id":2}' \
      http://localhost:8080/jsonrpc
    echo
    echo 'Kodi rescan triggered. Library updates run in the background; new albums appear within a few minutes.'
    ;;

  count)
    ssh $SSH_OPTS kip-nas "echo \"Albums in beets DB: \$(beet ls -a | wc -l)\""
    ;;

  *)
    cat <<EOF
Usage: nas-music-import.sh {status|prepare|check|cleanup|rescan|count}

  status    Show what's currently in the NAS staging dir
  prepare   Extract zips into per-album subfolders, list albums ready to import
  check     Flag any staged albums that already exist in the library
  cleanup   Remove staging dir after a successful beet import (only if no audio left)
  rescan    Trigger Kodi audio library clean+scan
  count     Print the total number of albums currently in beets

Typical workflow:
  1. From laptop: rsync ~/Downloads/Bandcamp/ nas@nas:$NAS_STAGING/
  2. nas-music-import.sh prepare
  3. nas-music-import.sh check
  4. SSH to NAS and run interactive import:
       ssh nas@nas
       beet import --noincremental $NAS_STAGING/
  5. nas-music-import.sh cleanup
  6. nas-music-import.sh rescan
EOF
    exit 1
    ;;
esac

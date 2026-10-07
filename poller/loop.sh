#!/bin/bash
# Long-running poll loop. GitHub only starts scheduled workflows when it feels like it, so instead of relying on
# a 30-minute cron, one job stays alive for ~5.5h and polls every 30 minutes itself. Fast boards every 30 min,
# slow boards (Workday etc.) every other round. A failed round never stops the loop.
cd "$(dirname "$0")"
END=$((SECONDS + 19800))
i=0
while [ $SECONDS -lt $END ]; do
  START=$SECONDS
  echo "=== round $i at $(date -u +%H:%M:%S) UTC"
  python poll.py --tier fast || echo "fast poll failed"
  if [ $((i % 2)) -eq 1 ]; then python poll.py --tier slow || echo "slow poll failed"; fi
  if [ -n "$CLAUDE_CODE_OAUTH_TOKEN$ANTHROPIC_API_KEY" ]; then python ai_score.py --max 60 --days 3 --workers 2 || echo "ai scoring failed"; fi
  i=$((i + 1))
  NEXT=$((START + 1800))
  [ $SECONDS -lt $NEXT ] && sleep $((NEXT - SECONDS))
done
echo "loop finished; the next scheduled run continues it"

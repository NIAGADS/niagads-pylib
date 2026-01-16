#!/bin/bash

# Default Configuration
DEFAULT_DAYS=2  # Default idle timeout in days
DEFAULT_CHECK_INTERVAL=3600  # Default check interval in seconds (1 hour)
DEFAULT_CONTAINERS=("seqrepo-rest-service" "uta")

# Function to display help message
print_help() {
  echo "Usage: $0 [OPTIONS]"
  echo ""
  echo "Monitor and stop idle Docker containers based on network activity."
  echo ""
  echo "Options:"
  echo "  --days <number>            Set the idle timeout in days (default: $DEFAULT_DAYS)."
  echo "  --check-interval <seconds> Set the interval in seconds to check for idle containers (default: $DEFAULT_CHECK_INTERVAL)."
  echo "  --containers <list>        Comma-separated list of container names to monitor (default: ${DEFAULT_CONTAINERS[*]})."
  echo "  --help                     Display this help message and exit."
  echo ""
  echo "Example:"
  echo "  nohup $0 --days 3 --check-interval 7200 --containers \"seqrepo-rest,uta\" > monitor_idle.log 2>&1 &"
  echo ""
  exit 0
}

# Parse Command-Line Arguments
DAYS=$DEFAULT_DAYS
CHECK_INTERVAL=$DEFAULT_CHECK_INTERVAL
CONTAINERS_TO_MONITOR=(${DEFAULT_CONTAINERS[@]})

while [[ $# -gt 0 ]]; do
  case $1 in
    --days)
      DAYS=$2
      shift 2
      ;;
    --check-interval)
      CHECK_INTERVAL=$2
      shift 2
      ;;
    --containers)
      IFS=',' read -r -a CONTAINERS_TO_MONITOR <<< "$2"
      shift 2
      ;;
    --help)
      print_help
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help to see usage instructions."
      exit 1
      ;;
  esac
done

# Convert days to seconds for idle timeout
IDLE_TIMEOUT=$((DAYS * 24 * 60 * 60))

declare -A IDLE_TIMERS

# Initialize idle timers for each container
for CONTAINER in "${CONTAINERS_TO_MONITOR[@]}"; do
  IDLE_TIMERS[$CONTAINER]=0
done

while true; do
  for CONTAINER in "${CONTAINERS_TO_MONITOR[@]}"; do
    # Check if the container is running
    if docker ps --filter "name=$CONTAINER" --filter "status=running" | grep -q "$CONTAINER"; then
      # Get network stats (rx_bytes + tx_bytes)
      NETWORK_ACTIVITY=$(docker exec "$CONTAINER" sh -c "cat /sys/class/net/eth0/statistics/rx_bytes /sys/class/net/eth0/statistics/tx_bytes" 2>/dev/null | awk '{sum += $1} END {print sum}')

      if [[ -z "$NETWORK_ACTIVITY" || "$NETWORK_ACTIVITY" -eq 0 ]]; then
        # Increment idle timer if no activity
        IDLE_TIMERS[$CONTAINER]=$((IDLE_TIMERS[$CONTAINER] + CHECK_INTERVAL))
        echo "$CONTAINER has been idle for ${IDLE_TIMERS[$CONTAINER]} seconds."

        if [[ ${IDLE_TIMERS[$CONTAINER]} -ge $IDLE_TIMEOUT ]]; then
          echo "Stopping idle container: $CONTAINER"
          docker stop "$CONTAINER"
        fi
      else
        # Reset idle timer if activity is detected
        IDLE_TIMERS[$CONTAINER]=0
      fi
    else
      echo "$CONTAINER is not running."
      IDLE_TIMERS[$CONTAINER]=0
    fi
  done

  sleep $CHECK_INTERVAL
done
#!/usr/bin/env bash

############################################################################
# Prints important log messages in cyan color; pink messages are generated
# by the local running deployment shell script, while cyan messages
# are generated by what is usually run inside of the Kubernetes pod.
# Arguments:
#   Info message
############################################################################
function emphasize {
  printf "\e[38;5;81m--- $1 ---\e[0m\n"
}

function exit_on_failure {
  # Catch k6 non-zero exit status and quit the rest of tests. For example, connection refused and threashold not met and, etc
  if [ ! -z $EXIT_ON_FAILURE ] && [ $1 != 0 ]
  then
    emphasize "Test failed"
    tail $ERROR_FILE
    cat $SUMMARY_FILE_JSON
    exit $1
  fi
}

emphasize "Creating Summary Directory"
if [[ -d summary ]]
then
    rm -rf summary
fi
mkdir summary

emphasize "Rendering K6 Files"
python3 -m perf_test.scripts.renderer -r render -t $TEMPLATE_DIR -s summary -c $CONFIG_FILE

emphasize "Creating Results Directory"
if [[ -d results ]]
then
    rm -rf results
fi
mkdir results

emphasize "Starting K6 Tests"
for TEST in render/*.js; do
  emphasize "Beginning K6 test: ${TEST}"
  RESULT_FILE=results/`basename "${TEST%.*}".txt`
  ERROR_FILE=results/`basename "${TEST%.*}".stderr`
  SUMMARY_FILE_JSON=summary/`basename "${TEST%.*}".json`
  K6_PROMETHEUS_REMOTE_URL=${K6_PROMETHEUS_REMOTE_URL}

  # Write StartTime to File
  date >> $RESULT_FILE
  # Then, run the test itself, dumping the important information into the result file

  if [[ -z $K6_PROMETHEUS_REMOTE_URL ]]; then
    echo "No K6_PROMETHEUS_REMOTE_URL was set, running default k6"
    k6 run $TEST --summary-export=$SUMMARY_FILE_JSON >> $RESULT_FILE 2>> $ERROR_FILE
  else
    echo "Sending K6 metrics to K6_PROMETHEUS_REMOTE_URL at ${K6_PROMETHEUS_REMOTE_URL}"
    ./k6_test/k6 run $TEST --summary-export=$SUMMARY_FILE_JSON -o output-prometheus-remote >> $RESULT_FILE 2>> $ERROR_FILE
  fi
  k6_status=$?

  # Write EndTime to File
  date >> $RESULT_FILE;

  emphasize "Intermediate test results for: ${TEST}"
  cat $RESULT_FILE

  if [ $? -eq 137 ]; then
    emphasize "ERROR: TEST $TEST WAS OOMKILLED; IT WILL NOT PRODUCE ANY RESULTS."
    rm $RESULT_FILE
  fi

  TEST_NO=$((TEST_NO+1))
  exit_on_failure $k6_status
  emphasize "Waiting 5s before next test"
  sleep 5
done

emphasize "Generating final Markdown for K6 tests..."
python3 -m perf_test.scripts.scraper -r results -s summary -c $CONFIG_FILE -p /app/persistent-results
# -k configs/kingdom.dict -p persistent-results 
# emphasize "K6 TESTS ARE COMPLETE. Use the following command to copy to your CWD."
# echo "kubectl cp ${POD_NAME}:output.md ./output.md && kubectl cp ${POD_NAME}:summary.json ./summary.json"

# Add a sleep at the end of the job to give time to exec into pods if need be
sleep 120
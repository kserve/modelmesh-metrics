# Performance Test

This is inspired by the internal Howitzer project, started by the Watson NLU team at IBM.

Howitzer is a collection of Bash/Python scripts which can be used for automating K6 load tests, and has the ability to scrape metrics and send to MLFlow (not yet implemented). Its primary purpose is to sequentially run a set of load tests and seamlessly aggregate the results into multiple human and machine readable formats, thereby reducing the tediousness of traversing a high number of load testing parameters or Kubernetes/Openshift configurations. A few examples of the types of parameters which Howitzer seeks to automate are given below.

- Non-iterable K6 parameters, i.e. duration and virtual users.

- Different target URLs and/or features.

- Different payload sizes.

## How Howitzer works
The core design principle beneath Howitzer lies in "exploding" K6 parameter iterables into a set of valid K6 test parameters, rendering each parameter combination into a Javascript object, and injecting the resulting object, along with other test information like the base URL being targeted, into a copy of a K6 template.

When the bash script `perf_test/runHowitzer.sh` is run, the bash script will create directories `render`, `results` and `summary`:
- `render` stores the "exploded" k6 tests using the k6 template specified in the test config for each k6_opts combination.
- Then the script will run each individual k6 test in this `render` directory, storing the human readable results as text in `results` directory.
- It will also store the corresponding json file of the result into `summary` directory.
- The `perf_test.scripts.scraper` script then consolidates the results from the K6 test, the input test conditions etc. into a single `summary.json` file for the tests that were run.

Example test config:
```json
{
  "rendering_configs": {
    "title":"K6 Model Mesh Inference Tests",
    "description": "Example to launch groups of perf tests."
  },
  "test_configs": [
    {
      "name": "0-warmup",
      "description": "Warm up sklearn model for 30s with 1 vu and 2vus",
      "template": "grpc/script_grpc_skmnist.js",
      "payload": "1by64payloadSklearn.json",
      "base_url": "localhost:8033",
      "model_name": "snapml-mnist-svm",
      "k6_opts": {
        "vus":[1,5],
        "duration":"30s"
      }
    }
  ]
}
```
This config will explode into 2 individual k6 tests as individual files in the `render` folder: Test 0 with 1 vu, duration 30s. And test 1 with 5vus, duration 30s.
Both tests use the same payload `1by64payloadSklearn.json`, same base_url `localhost:8033` and the same test template `grpc/script_grpc_skmnist.js`.

## Unit testing the Howitzer rendered script

We also wrote unit tests for the script. The tests are in `unit_test` folder, and can be tested with:

```python
python3 -m unittest unit_test/k6/test_renderer.py
```

## Local Howitzer run
Howitzer uses [Pipenv](https://pipenv.pypa.io/en/latest/install/#installing-pipenv) to manage its python environment. After installing pipenv, install dependencies with pipenv sync, then use pipenv run or pipenv shell to execute scripts within the Pipenv managed environment.

- To explode and render the template into k6 scripts locally, set the `CONFIG_FILE` and `TEMPLATE_DIR` env vars to the name of the file in the configs directory and the test template dir respectively that you want to run.
```sh
export TEMPLATE_DIR=k6_test/
export CONFIG_FILE=perf_test/configs/inference-test.json
```

- Optionally, to send k6 metrics to an available Prometheus that accepts remote write, set the env var `K6_PROMETHEUS_REMOTE_URL`. This example assumes the Prometheus service is running and port forwarded to at localhost:9090 
```sh
export K6_PROMETHEUS_REMOTE_URL=http://localhost:9090/api/v1/write
```

- Now, you can run Howitzer with:
```sh
./perf_test/runHowitzer.sh
```
"""This module scrapes the K6 test results and aggregates them into a Markdown
document that is well-organized and easily read. The output of this module
is the deliverable of a Howitzer launch.

echo $CONFIG_FILE 
perf_test/configs/inference-test.json

python3 -m perf_test.scripts.scraper -r results -s summary -c $CONFIG_FILE 
"""
import argparse
import json
import os
import sys
import textwrap
import re
import shutil

TEST_CONFIGS_FILENAME = 'test_configs.dict'
OUTPUT_FILENAME = 'output.md'
SUMMARY_FILENAME = 'summary.json'

# Between K6_DELIMITER_INIT_START and K6_DELIMITER_INIT_END is the init info section
# with VU, duration info, etc.
# After K6_DELIMITER_CHECKS is the checks info
K6_DELIMITER_INIT_START = '.io'
K6_DELIMITER_INIT_END = 'running'
K6_DELIMITER_CHECKS = 'default ✓'
SECTION_HEADER = '<!---MD_SECTION--->'

def retrieve_k6_results(data, start_time, end_time):
    """Extracts raw information from the K6 test. Howitzer pipes the K6 output from
    stdout only. Currently, K6 tends to use the following as delimiters for
    processing: [----------------------------------------------------------].
    This occurs when the test is loading options, as well as when it is starting.
    We use this delimiter to remove the splash screen ASCII art, parse out the
    inital params (i.e. num virtual users, duration, and so on), as well as the
    load test's results. The result is a formatted string. NOTE: Although the
    Markdown string is formatted in yaml, the result is NOT yaml; it just happens
    to align well with the way K6 prints results out.

    Parameters:
        data (list): List of lines in the K6 file output file being read.
        start_time (str): Date at which the K6 test being considered began.
        end_time (str): Date at which the K6 test being considered ended.

    Returns:
         str: Formatted code block (with date info) to be rendered into Markdown.
    """
    init_start_idx = [i for i, val in enumerate(data) if K6_DELIMITER_INIT_START in val][-1]
    init_end_idx = [i for i, val in enumerate(data) if K6_DELIMITER_INIT_END in val][0]
    check_idx = [i for i, val in enumerate(data) if K6_DELIMITER_CHECKS in val][0]
    init_info = [x for x in data[init_start_idx+1:init_end_idx]]
    results = [x for x in data[check_idx+1:]]
    formatted = textwrap.dedent(''.join(init_info + ['\n'] + results))
    start_tstr = 'Test start time: {}'.format(start_time)
    end_tstr = 'Test end time: {}'.format(end_time)
    return '\n```yaml\n{}{}{}```'.format(formatted, start_tstr, end_tstr)


def write_document_intro(json_configs, out_file):
    """Writes the header of the output markdown file, which consists of the overall
    objective and the JSON file required for reproducing the tests.

    Args:
        json_configs (dict): parsed JSON configuration file.
        out_file (file): opened output file being written.
    """
    if 'rendering_configs' not in json_configs:
        raise KeyError('Rendering configs not present in configmap! Scraping failed.')
    out_file.write('# ' + json_configs['rendering_configs']['title'] + '\n')
    out_file.write(SECTION_HEADER + '\n')
    if 'description' in json_configs['rendering_configs']:
        out_file.write(json_configs['rendering_configs']['description'] + '\n ')
    out_file.write('## JSON Used by Howitzer Configmap \n')
    out_file.write('```json\n'+json.dumps(json_configs, indent=2, sort_keys=True)+'\n```\n')

def write_document_tests(json_configs, out_file, results_dir: str):
    """Writes the remainder of the file (K6 test results). Groups each named block
    as they are defined in the config file. Also renders in optional block
    descriptions.

    Args:
        json_configs (dict): parsed JSON configuration file.
        out_file (file): opened output file being written.
    """
    if 'test_configs' not in json_configs:
        raise KeyError('Rendering configs not present in configmap! Scraping failed.')
    result_files = [x for x in os.listdir(results_dir) if x.endswith(".txt")]
    out_file.write(SECTION_HEADER + '\n')
    out_file.write('## Load Test Results')
    # Iterate over all testing groups. Make a drop down menu for each one.
    for test_opts in json_configs['test_configs']:
        out_file.write('\n<details>\n')
        out_file.write('<summary>'+ test_opts['name'] +'</summary>\n')
        if 'description' in test_opts:
            out_file.write(test_opts['description'] + '\n\n')
        # Iterate over all K6 subtests that were rendered and processed.
        matching_files = [x for x in result_files if x[:x.rindex('_')] == test_opts['name']]
        for res_file in natural_sort(matching_files):
            with open(os.path.join(results_dir, res_file), 'r') as results:
                start_time, *contents, end_time = results.readlines()
                k6_dump = retrieve_k6_results(contents, start_time, end_time)
                out_file.write('{}\n\n'.format(k6_dump))
        out_file.write('</details>\n')

def natural_sort(filenames):
    """Naturally sorts the filenames so that they appear in a logical order once they
    are rendered into the output markdown document.

    Args:
        filenames (list): list of filenames to be sorted.
    """
    convert = lambda x: int(x) if x.isdigit() else x.lower()
    alphanum_key = lambda x: [ convert(c) for c in re.split('([0-9]+)', x) ]
    return sorted(filenames, key = alphanum_key)

def generate_md_output(config_file: str, results_dir: str):
    """Writes the output document to be retrieved by the user after running K6 tests.
    The document will be stored in the top level Howitzer directory.
    """
    config_contents = json.load(open(config_file, 'r'))
    with open(OUTPUT_FILENAME, 'w') as out_file:
        write_document_intro(config_contents, out_file)
        write_document_tests(config_contents, out_file, results_dir)

def write_summary_tests(summaries_dir: str, json_configs, out_file, results_dir: str):
    """Writes the summary.json file with consolidated test info, config and results

    Args:
        json_configs (dict): parsed JSON configuration file.
        out_file (file): opened output file being written.
    """
    if 'rendering_configs' not in json_configs:
        raise KeyError('Rendering configs with title and description not present in configmap! Scraping failed.')

    summary_files = [x for x in os.listdir(summaries_dir) if x[-4:] == 'json']
    test_configs_file = os.path.join(summaries_dir, TEST_CONFIGS_FILENAME)
    test_configs = json.load(open(test_configs_file, 'r'))
    summary_configs = {}

    # Iterate over all testing summaries and adds test info, config and results for each test
    for test_summary in summary_files:
        test_name = test_summary[:-5]
        summary_configs[test_name] = {}

        if 'rendering_configs' in json_configs:
            summary_configs[test_name]['rendering_configs'] = json_configs['rendering_configs']

        summary_configs[test_name] = test_configs[test_name]

        #Get start and end time for test from test result file in RESULTS_DIR
        with open(os.path.join(results_dir, test_name + '.txt'), 'r') as result_file:
            start_time, *contents, end_time = result_file.readlines()
        if start_time: summary_configs[test_name]['start_time'] = start_time.strip()
        if end_time: summary_configs[test_name]['end_time'] = end_time.strip()

        summary_configs[test_name]['test_results'] = json.load(open(os.path.join(summaries_dir, test_name + '.json'), 'r'))

        # Per k6 version 0.31.0, we don't support the http_req_duration sub-metric with label: http_req_duration{expected_response:true}
        if "http_req_duration{expected_response:true}" in summary_configs[test_name]['test_results']["metrics"]:
            del summary_configs[test_name]['test_results']["metrics"]["http_req_duration{expected_response:true}"]

    json.dump(summary_configs, out_file, indent = 4)
    print("Dumping json results to a log line for persistence in logDNA")
    print(json.dumps(summary_configs))

def generate_summary_output(summaries_dir: str, config_file: str, results_dir: str):
    """Writes the output summary document to be retrieved by the user after running K6 tests.
    The document will be stored in the top level Howitzer directory.
    """
    config_contents = json.load(open(config_file, 'r'))
    with open(SUMMARY_FILENAME, 'w') as out_file:
        write_summary_tests(summaries_dir, config_contents, out_file, results_dir)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(add_help=False,
                                     description=
                                     'Render some mother trucking K6 tests.')

    parser.add_argument('--help', action='help', help='Show this help message and exit.')

    parser.add_argument('-r', '--results-dir', metavar='RESULTS_DIR',
                        help='The directory to find the k6 test results in',
                        required=True)
    parser.add_argument('-s', '--summaries-dir', metavar='SUMMARIES_DIR',
                        help='The directory to place the k6 per-test summary files into',
                        required=True)
    parser.add_argument('-c', '--config-file', metavar='CONFIG_FILE',
                        help='The absolute path to the one true test config file to be exploded',
                        required=True)
    parser.add_argument('-p', '--persistent-results-dir', metavar='PERSISTENT_RESULTS_DIR',
                        help='Absolute path to the persistant storage location where to store the summary.json for later consumption',
                        required=False)

    args = parser.parse_args()

    generate_md_output(args.config_file, args.results_dir)
    generate_summary_output(args.summaries_dir, args.config_file, args.results_dir)
    
    if args.persistent_results_dir is not None:
        persistent_dir = args.persistent_results_dir
        print(f"Persistent dir path set to: {persistent_dir}")

        if os.path.exists(persistent_dir):
            shutil.copyfile(SUMMARY_FILENAME, os.path.join(persistent_dir, SUMMARY_FILENAME))
        else:
            print(f"Supplied path {persistent_dir} does not exist.")
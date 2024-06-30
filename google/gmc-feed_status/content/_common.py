# helper imports
from __future__ import print_function
import argparse
from urllib.parse import urljoin
import json
import logging
import os
import random
import sys
import time

# google imports
import google_auth_httplib2
from googleapiclient import discovery
from googleapiclient import errors
from googleapiclient import http
from googleapiclient import model

# local imports
from . import _constants
from . import _auth

def read_merchant_ids(file_path):
    with open(file_path, 'r') as file:
        merchant_ids = json.load(file)
    return merchant_ids

def init(argv, doc, parents=None, sandbox=False):
  service = None
  sandbox_service = None
  flags = None
  parent_parsers = []
  if parents is not None:
    parent_parsers.extend(parents)

  parser = argparse.ArgumentParser(
      description=doc,
      formatter_class=argparse.RawDescriptionHelpFormatter,
      parents=parent_parsers)
  parser.add_argument(
      '--config_path',
      metavar='PATH',
      default=os.path.dirname(os.path.realpath(__file__)),
      help='configuration directory')
  parser.add_argument(
      '--noconfig',
      action='store_true',
      help='run with no configuration directory')
  parser.add_argument(
      '--log_file',
      metavar='FILE',
      help='filename for logging API requests and responses'
  )
  flags = parser.parse_args(argv[1:])
  base_dir = os.path.dirname(os.path.realpath(__file__))
  auth_path = os.path.join(base_dir, _constants.AUTH_DIR)
  if flags.log_file:
    logging.basicConfig(filename=flags.log_file, level=logging.INFO)
    model.dump_request_response = True
  config = {'path': auth_path, 'config_path': flags.config_path}
  if not flags.noconfig:
      if not os.path.isdir(flags.config_path):
          print(
              'Configuration directory "%s" does not exist.' % flags.config_path,
              file=sys.stderr)
          sys.exit(1)

      if not os.path.isdir(auth_path):
          print(
              'Content API configuration directory "%s" does not exist.' %
              auth_path,
              file=sys.stderr)
          sys.exit(1)
      config_file = os.path.join(auth_path, _constants.CONFIG_FILE)
      if not os.path.isfile(config_file):
          print('Configuration file %s does not exist.' % config_file)
          print('Falling back to configuration based on authenticated user.')
      else:
          loaded_config = json.load(open(config_file, 'r'))
          if isinstance(loaded_config, list):
              # If the loaded configuration is a list, extract the relevant information
              loaded_config = {'merchantId': loaded_config[0]['merchantId']}
          config.update(loaded_config)
  credentials = _auth.authorize(config)
  auth_http = google_auth_httplib2.AuthorizedHttp(
      credentials, http=http.set_user_agent(
          http.build_http(), _constants.APPLICATION_NAME))
  if _constants.ENDPOINT_ENV_VAR in os.environ:
    # Strip off everything after the host/port in the URL.
    root_url = urljoin(
        os.environ[_constants.ENDPOINT_ENV_VAR],
        '/')
    print('Using non-standard root for API discovery: %s' % root_url)
    discovery_url = root_url + '/discovery/v1/apis/{api}/{apiVersion}/rest'
    service = discovery.build(
        _constants.SERVICE_NAME,
        _constants.SERVICE_VERSION,
        discoveryServiceUrl=discovery_url,
        http=auth_http)
    if sandbox:
      sandbox_service = discovery.build(
          _constants.SERVICE_NAME,
          _constants.SANDBOX_SERVICE_VERSION,
          discoveryServiceUrl=discovery_url,
          http=auth_http)
  else:
    service = discovery.build(
        _constants.SERVICE_NAME, _constants.SERVICE_VERSION, http=auth_http)
    if sandbox:
      sandbox_service = discovery.build(
          _constants.SERVICE_NAME,
          _constants.SANDBOX_SERVICE_VERSION,
          http=auth_http)
  retrieve_remaining_config_from_api(service, config)
  return (sandbox_service if sandbox else service, config, flags)
unique_id_increment = 0

def get_unique_id():
  """Generates a unique ID.
  The ID is based on the current UNIX timestamp and a runtime increment.
  Returns:
    A unique string.
  """
  global unique_id_increment
  if unique_id_increment is None:
    unique_id_increment = 0
  unique_id_increment += 1
  return '%d%d' % (int(time.time()), unique_id_increment)

def retrieve_remaining_config_from_api(service, config):
  """Retrieves any missing configuration information using API calls.

  This function can fill in the following configuration fields:
  * merchantId

  It will also remove or overwrite existing values for the following fields:
  * isMCA
  * websiteUrl

  Args:
    service: Content API service object
    config: dictionary, Python representation of config JSON.
  """
  # handle IDs if list or dict
  if isinstance(config, list):
      config = {'merchantId': config[0]['merchantId']}
  elif not isinstance(config, dict):
      print('Invalid configuration format. Expected a dictionary or a list.')
      sys.exit(1)
  authinfo = service.accounts().authinfo().execute()
  account_ids = authinfo.get('accountIdentifiers')
  if not account_ids:
    print('The currently authenticated user does not have access to any Merchant Center accounts.')
    sys.exit(1)
  merchant_id = config.get('merchantId')
  if not merchant_id:
      print('Merchant ID is missing in the configuration.')
      sys.exit(1)
  config['merchantId'] = int(merchant_id)
  merchant_id = config['merchantId']
  config['isMCA'] = False
  # The requested Merchant Center can only be an MCA if we are a
  # user of it (and thus have access) and it is listed as an
  # aggregator in authinfo.
  for account_id in authinfo['accountIdentifiers']:
      if 'aggregatorId' in account_id and int(account_id['aggregatorId']) == merchant_id:
          config['isMCA'] = True
          break
      if 'merchantId' in account_id and int(account_id['merchantId']) == merchant_id:
          break
  '''
  if config['isMCA']:
      print('Merchant Center %d is an MCA.' % config['merchantId'])
  else:
      print('Merchant Center %d is not an MCA.' % config['merchantId'])
  '''
  account = service.accounts().get(merchantId=merchant_id, accountId=merchant_id).execute()
  config['websiteUrl'] = account.get('websiteUrl')
  '''
  if not config['websiteUrl']:
      print('No website for Merchant Center %d.' % config['merchantId'])
  else:
      print('Website for Merchant Center %d: %s' % (config['merchantId'], config['websiteUrl']))
  '''

def is_mca(config):
  return config.get('isMCA', False)

def check_mca(config, should_be_mca, msg=None):
  """Checks that the configured account is an MCA or not based on the argument.

  If not, it exits the program early.

  Args:
    config: dictionary, Python representation of config JSON.
    should_be_mca: boolean, whether or not we expect an MCA.
    msg: string, message to use instead of standard error message if desired.
  """
  if should_be_mca != is_mca(config):
    if msg is not None:
      print(msg)
    else:
      print('For this sample, you must%s use a multi-client account.' %
            '' if should_be_mca else ' not')
    sys.exit(1)


def retry_request(req, slot_time=5.0, max_time=60.0):
  """Retries the provided request for HTTP errors.

  Normally, we could just use the optional num_retries keyword for the
  execute() methods. However, the only 4xx errors they retry are
  429s (always) and 403s (sometimes). Unfortunately, the Content API
  sometimes returns other 4xx messages: for example, it will return 401
  if you try to retrieve a new sub-account after creating it
  before it is fully available. Here, we just retry as long as we get
  an HTTP error.

  Args:
    req: HTTP request to retry
    slot_time: float, slot time (in seconds) for retries
    max_time: float, max time (in seconds) to retry

  Returns:
    The same result as the original request, if successful.
  """
  waited_time = 0.0
  retry_num = 0
  while True:
    try:
      return req.execute()
    except errors.HttpError as e:
      if waited_time >= max_time:
        raise e
      else:
        sleep_time = random.randint(0, 2 ** retry_num - 1) * slot_time
        # Cap the sleep time to avoid overrunning the max time by too long.
        if waited_time + sleep_time > max_time:
          sleep_time = max_time - waited_time
        print('Request failed, trying again after %.2f seconds.' % sleep_time)
        time.sleep(sleep_time)
        waited_time += sleep_time
        retry_num += 1
        continue

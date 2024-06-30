# Constants for configuration
AUTH_DIR = 'authfiles'
CONFIG_FILE = 'merchant-info.json'
TOKEN_FILE = 'stored-token.json'
APPLICATION_NAME = 'GMC-feeds_status_report'

# Constants for authentication
CLIENT_SECRETS_FILE = 'client-secrets.json'
SERVICE_ACCOUNT_FILE = 'service-account.json'

# Constants needed for the Content API
SERVICE_NAME = 'content'
SERVICE_VERSION = 'v2.1'
SANDBOX_SERVICE_VERSION = 'v2.1sandbox'
CONTENT_API_SCOPE = 'https://www.googleapis.com/auth/' + SERVICE_NAME

# These constants define the identifiers for all of our example products/feeds.

# The products will be sold online.
CHANNEL = 'online'
# The product details are provided in English.
CONTENT_LANGUAGE = 'en'
# The products are sold in the USA.
TARGET_COUNTRY = 'US'

# Environment variable used for testing against different endpoints.
ENDPOINT_ENV_VAR = 'GOOGLE_SHOPPING_SAMPLES_ENDPOINT'

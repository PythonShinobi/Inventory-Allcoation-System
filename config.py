import os


def get_api_url() -> str:
    """
    Return the base URL of the running allocation API.

    The API URL can be configured through the API_URL environment
    variable. If it is not provided, localhost is used.

    Example:
        >>> get_api_url()
        'http://localhost:5000'
    """
    
    return os.environ.get("API_URL", "http://localhost:5000")